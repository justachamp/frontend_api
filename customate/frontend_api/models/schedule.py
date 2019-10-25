import logging
import datetime
import arrow
from dataclasses import dataclass

from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import RegexValidator
from enumfields import EnumField
from django.db import models
from django.db.models import Sum, Q
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from core.models import Model, User
from core.fields import Currency, PaymentStatusType, FundingSourceType, PayeeType
from frontend_api.fields import SchedulePurpose, SchedulePeriod, ScheduleStatus, SchedulePaymentType
from customate.settings import CELERY_BEAT_SCHEDULE
from frontend_api.models.blacklist import BlacklistDate, BLACKLISTED_DAYS_MAX_RETRY_COUNT

logger = logging.getLogger(__name__)

SCHEDULES_START_PROCESSING_TIME = CELERY_BEAT_SCHEDULE["once_per_day"]["schedule"]  # type: celery.schedules.crontab


class AbstractSchedule(Model):
    class Meta:
        # https://stackoverflow.com/questions/3254436/django-model-mixins-inherit-from-models-model-or-from-object
        abstract = True

    name = models.CharField(_('schedule name'), max_length=150)
    status = EnumField(ScheduleStatus)
    origin_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        blank=False,
        related_name='%(class)s_payed_by_me'
    )  # type: User
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name='%(class)s_payed_to_me'
    )  # type: User
    purpose = EnumField(SchedulePurpose)
    currency = EnumField(Currency)
    payee_id = models.UUIDField(help_text=_("Money recipient"))
    payee_title = models.CharField(max_length=100, default='')
    payee_recipient_name = models.CharField(max_length=254, default='')
    payee_recipient_email = models.CharField(max_length=254, default='')
    payee_iban = models.CharField(max_length=50, default='')
    payee_type = EnumField(PayeeType, max_length=50)

    funding_source_id = models.UUIDField(default=None, blank=True, null=True)
    funding_source_type = EnumField(FundingSourceType, max_length=50, default=None, blank=True, null=True)

    backup_funding_source_id = models.UUIDField(default=None, blank=True, null=True)
    backup_funding_source_type = EnumField(FundingSourceType, max_length=50, default=None, blank=True, null=True)

    period = EnumField(SchedulePeriod)
    number_of_payments = models.PositiveIntegerField(
        default=0, help_text=_("Initial number of payments in the current schedule set upon creation.")
    )
    number_of_payments_made = models.PositiveIntegerField(
        default=0, help_text=_("Number of payments made in the current schedule. Changes dynamically in time")
    )
    start_date = models.DateField()
    payment_amount = models.PositiveIntegerField()
    payment_fee_amount = models.PositiveIntegerField(
        default=0, help_text=_("Approximate fee amount for regular payment in schedule")
    )
    deposit_amount = models.PositiveIntegerField(
        null=True, help_text=_("Initial payment independent of the rest of scheduled payments")
    )
    deposit_fee_amount = models.PositiveIntegerField(
        default=0, help_text=_("Approximate fee amount for deposit payment in schedule")
    )
    deposit_payment_date = models.DateField(null=True)  # This should be strictly < start_date
    additional_information = models.CharField(max_length=250, blank=True, null=True,
                                              validators=[RegexValidator(regex=r'^([a-zA-Z0-9\/\-\?\:\.\+ ]*)$',
                                                                         message='Field contains forbidden characters')])
    is_overdue = models.BooleanField(
        default=False,
        help_text=_('Indicates whether the schedule has overdue payments'),
    )
    is_processing = models.BooleanField(
        default=False,
        help_text=_('Preventing users from starting "pay overdue" process several times at once'),
    )

    def __str__(self):
        return "Schedule(id=%s, period=%s, amount=%s, deposit_amount=%s, start_date=%s)" % (
            self.id, self.period, self.payment_amount, self.deposit_amount, self.start_date
        )

    @property
    def deposit_additional_information(self):
        if self.additional_information is not None and self.additional_information != '':
            return f'Deposit for {self.additional_information}'
        else:
            return 'Deposit'


class Schedule(AbstractSchedule):
    ACTIVE_SCHEDULE_STATUSES = [ScheduleStatus.open, ScheduleStatus.pending]
    PROCESSABLE_SCHEDULE_STATUSES = [ScheduleStatus.open]

    @property
    def total_sum_to_pay(self) -> int:
        """
        Total sum that should be paid by this schedule
        :return:
        """
        return self.total_fee_amount + \
               (self.deposit_amount if self.deposit_amount is not None else 0) + \
               (self.payment_amount * self.number_of_payments)

    @property
    def total_paid_sum(self) -> int:
        """
        Total sum of all Schedule's paid payments
        :return:
        """
        res = LastSchedulePayments.objects.filter(
            schedule_id=self.id,
            payment_status__in=[PaymentStatusType.SUCCESS]
        ).aggregate(Sum('original_amount'))
        total = res.get('original_amount__sum')
        return total if total else 0

    @property
    def total_fee_amount(self) -> int:
        return (self.payment_fee_amount * self.number_of_payments) + self.deposit_fee_amount

    def is_stoppable(self):
        return self.status in [ScheduleStatus.open]

    def _did_we_send_first_payment(self):
        """
        TODO: Rewrite to fully rely on actual data in SchedulePayments instead of date comparison
        :return:
        """
        # return self.number_of_payments_made > 0 # we can't rely on this field here, since there is
        # a case of long-running PENDING payments(days), which might corrupt our next_payment_date calculations
        now_date = arrow.utcnow().datetime.date()
        # We cannot just compare dates and ignore time. If start_date is current date
        # then scheduler's start time is important in fact
        return now_date > self.start_date or (
                now_date == self.start_date and arrow.utcnow() > self._get_celery_processing_time()
        )

    @property
    def number_of_payments_left(self):
        self.refresh_number_of_payments_made()
        return self.number_of_payments - self.number_of_payments_made

    @property
    def next_payment_date(self):
        """
        TODO2: Take into account last_payment_date (instead of start_date)
        :return:
        :rtype: datetime.date|None
        """
        res = None
        # If we didn't make any payments yet then factor is 1 (which transforms into: next week, next month etc.)
        period_shift_factor = max(1, self.number_of_payments_made)

        if not (self.status in [ScheduleStatus.open] and self.number_of_payments_left != 0):
            res = None
        elif self.period is SchedulePeriod.one_time or not self._did_we_send_first_payment():
            res = arrow.get(self.start_date)
        elif self.period is SchedulePeriod.weekly:
            res = arrow.get(self.start_date).replace(weeks=+period_shift_factor)
        elif self.period is SchedulePeriod.monthly:
            res = arrow.get(self.start_date).replace(months=+period_shift_factor)
            # Note how JAN->FEB is handled in following example:
            # <Arrow [2019-01-31T11:58:11.459665+00:00]> -> <Arrow [2019-02-28T11:58:11.459665+00:00]>
        elif self.period is SchedulePeriod.quarterly:
            res = arrow.get(self.start_date).replace(months=+(4 * period_shift_factor))
        elif self.period is SchedulePeriod.yearly:
            res = arrow.get(self.start_date).replace(years=+period_shift_factor)

        return res.datetime.date() if res else None

    @property
    def payment_type(self):
        """
        Returns schedule payment type. Helpful for the client to be able to calculate different fees when selecting
        funding source(s)
        :return:
        """
        if self.payee_type is PayeeType.WALLET:
            return str(SchedulePaymentType.internal.value)
        return str(SchedulePaymentType.external.value)

    @property
    def origin_payment_account_id(self):
        return self.origin_user.account.payment_account_id

    @property
    def recipient_payment_account_id(self):
        return self.recipient_user.account.payment_account_id

    def move_to_status(self, status: ScheduleStatus):
        old_status = self.status
        self.status = status
        self.save(update_fields=["status"])
        logger.info("Updated Schedule(id=%s) status=%s(was=%s)" % (self.id, status, old_status))

    @property
    def processing(self) -> bool:
        return self.is_processing

    @processing.setter
    def processing(self, value: bool):
        old_val = self.is_processing
        self.is_processing = value
        self.save(update_fields=["is_processing"])
        logger.info("Updated schedule(id=%s) is_processing=%s(was=%s)" % (self.id, value, old_val))

    @property
    def overdue(self) -> bool:
        return self.is_overdue

    @overdue.setter
    def overdue(self, value: bool):
        old_val = self.is_overdue
        self.is_overdue = value
        self.save(update_fields=["is_overdue"])
        logger.info("Updated schedule(id=%s) is_overdue=%s(was=%s)" % (self.id, value, old_val))

    def refresh_number_of_payments_made(self):
        """
        Update count of actual payments made in the DB
        :return:
        """
        # get the list of last successful, regular payments
        self.number_of_payments_made = LastSchedulePayments.objects.filter(
            schedule_id=self.id,
            payment_status__in=[PaymentStatusType.SUCCESS],
            is_deposit=False
        ).count()
        self.save(update_fields=["number_of_payments_made"])

    def update_status(self) -> ScheduleStatus:
        """
        Update Schedule's status based on aggregated info about all underlying payments (see SchedulePayments model).
        This is in fact, state machine. We could only migrate from one specific state into another.

        Possible Schedule statuses
          'open', there are some future planned payments and all past payments are successful
          'closed' there are NO future planned payments and all past payments are successful
          'stopped', regardless of underlying payments statuses schedule is stopped by user

        :return: new Schedule status
        :rtype: ScheduleStatus
        """
        logger.info("Updating schedule(id=%s) with status=%s" % (self.id, self.status))

        # get the list of last payments
        last_payments = LastSchedulePayments.objects.filter(
            schedule_id=self.id,
        ).order_by("created_at")  # type: list[LastSchedulePayments]
        statuses = [lp.payment_status for lp in last_payments]  # type: List[LastSchedulePayments]
        logger.info("Got the list of last payments(schedule_id=%s): %r" % (
            self.id,
            {lp.id: lp.payment_status for lp in last_payments}
        ))

        if len(statuses) == 0:
            # ignore any status updates
            logger.info("Leaving schedule(id=%s) with unchanged status=%s, since there are no last payments made" % (
                self.id, self.status
            ))
            return self.status

        if any([s in [PaymentStatusType.FAILED, PaymentStatusType.REFUND, PaymentStatusType.CANCELED] for s in
                statuses]):
            # mark schedule as overdue and return current status
            self.overdue = True
            return self.status

        # if we've gone so far, we're definitely not overdue anymore
        self.overdue = False

        # no need to lookup particular payment statuses, if we are either
        #  a) 'stopped' by user
        #  b) 'closed' (all scheduled payments were successfully made)
        if self.status in [ScheduleStatus.stopped, ScheduleStatus.closed]:
            # ignore any status updates
            logger.info("Leaving schedule(id=%s) with unchanged status=%s" % (self.id, self.status))
            return self.status

        if all([s in [PaymentStatusType.SUCCESS, PaymentStatusType.PENDING, PaymentStatusType.PROCESSING] for s in
                statuses]) and self.number_of_payments_left != 0:
            # mark schedule as open(default state)
            self.move_to_status(ScheduleStatus.open)
            return ScheduleStatus.open

        if self.number_of_payments_left == 0:
            self.move_to_status(ScheduleStatus.closed)
            return ScheduleStatus.closed

        return self.status

    def accept(self, payment_fee_amount, deposit_fee_amount, funding_source_id, funding_source_type,
               backup_funding_source_id, backup_funding_source_type):
        """
        This is a 'receive' funds scenario
        :param payment_fee_amount:
        :param deposit_fee_amount:
        :param funding_source_id:
        :param funding_source_type:
        :param backup_funding_source_id:
        :param backup_funding_source_type:
        :return:
        """
        # accept schedules in 'PENDING' status only
        if self.status != ScheduleStatus.pending:
            raise ValidationError(f'Cannot accept schedule with current status (status={self.status})')
        # TODO: check for 'scenario' type: it should be 'receive funds'
        self.move_to_status(ScheduleStatus.open)

        self.payment_fee_amount = payment_fee_amount
        self.deposit_fee_amount = deposit_fee_amount
        self.funding_source_id = funding_source_id
        self.funding_source_type = funding_source_type
        self.backup_funding_source_id = backup_funding_source_id
        self.backup_funding_source_type = backup_funding_source_type
        self.save(update_fields=["payment_fee_amount", "deposit_fee_amount", "funding_source_id", "funding_source_type",
                                 "backup_funding_source_id", "backup_funding_source_type"])

    def reject(self):
        # reject schedules in 'PENDING' status only
        if self.status != ScheduleStatus.pending:
            raise ValidationError(f'Cannot reject schedule with current status (status={self.status})')

        self.move_to_status(ScheduleStatus.rejected)

    @staticmethod
    def has_active_schedules_with_source(funding_source_id):
        return Schedule.objects.filter(
            funding_source_id=funding_source_id,
            status__in=Schedule.ACTIVE_SCHEDULE_STATUSES
        ).exists()

    @staticmethod
    def has_active_schedules_with_payee(payee_id):
        return Schedule.objects.filter(
            payee_id=payee_id,
            status__in=Schedule.ACTIVE_SCHEDULE_STATUSES
        ).exists()

    @staticmethod
    def close_user_schedules(user_id):
        logger.info(f"Closing user's(id={user_id}) schedules")
        Schedule.objects.filter(Q(recipient_user__id=user_id) | Q(origin_user__id=user_id)) \
            .update(status=ScheduleStatus.closed)

    @staticmethod
    def _get_celery_processing_time():
        st_hour = int(list(SCHEDULES_START_PROCESSING_TIME.hour)[0])
        st_minute = int(list(SCHEDULES_START_PROCESSING_TIME.minute)[0])
        return arrow.get("{full_date}T{hour}:{minute}:00".format(
            full_date=arrow.utcnow().format("YYYY-MM-DD"),
            hour=st_hour,
            minute=st_minute
        ), ['YYYY-MM-DDTH:mm:ss', 'YYYY-MM-DDTH:m:ss', 'YYYY-MM-DDTHH:m:ss'])

    def have_time_for_payments_processing(self):
        return self.have_time_for_deposit_payment_processing() and self.have_time_for_regular_payment_processing()

    def have_time_for_deposit_payment_processing(self):
        if self.deposit_payment_date is None:
            return True

        have_made_deposit_payment = LastSchedulePayments.objects.filter(
            schedule_id=self.id,
            is_deposit=True
        ).exists()

        if have_made_deposit_payment:
            return True

        deposit_payment = DepositsSchedule.objects.get(
            pk=self.id,
            status=ScheduleStatus.open.value
        )
        scheduled_date = arrow.get(deposit_payment.scheduled_date).datetime.date()
        return scheduled_date >= Schedule.nearest_scheduler_processing_date()

    def have_time_for_regular_payment_processing(self):
        try:
            number_of_sent_regular_payments = SchedulePayments.objects.filter(
                schedule_id=self.id,
                parent_payment_id=None,
                is_deposit=False
            ).count()

            if number_of_sent_regular_payments == self.number_of_payments:
                return True

            # Selecting nearest scheduled date for regular payments, by skipping dates for which
            # we already sent payments
            from_index = number_of_sent_regular_payments
            to_index = from_index + 1
            nearest_payment = self.schedule_cls_by_period.objects.filter(
                id=self.id,
                status=ScheduleStatus.open,
            ).order_by("scheduled_date").all()[from_index:to_index].first()

            scheduled_date = arrow.get(nearest_payment.scheduled_date).datetime.date()
            return nearest_payment is not None and scheduled_date >= Schedule.nearest_scheduler_processing_date()
        except ObjectDoesNotExist:
            return False

    @staticmethod
    def nearest_scheduler_processing_date():
        """
        Find out nearest schedulers processing time (taking into account blacklisted dates)
        :return: datetime.date
        """
        scheduler_start_time = Schedule._get_celery_processing_time()
        retry_count = 1

        while True:
            if retry_count > BLACKLISTED_DAYS_MAX_RETRY_COUNT:
                break

            if BlacklistDate.contains(scheduler_start_time.datetime.date()) or arrow.utcnow() > scheduler_start_time:
                scheduler_start_time = scheduler_start_time.shift(days=1)
            else:
                break

        return scheduler_start_time.datetime.date()

    @property
    def schedule_cls_by_period(self):
        return {
            SchedulePeriod.one_time: OnetimeSchedule,
            SchedulePeriod.weekly: WeeklySchedule,
            SchedulePeriod.monthly: MonthlySchedule,
            SchedulePeriod.quarterly: QuarterlySchedule,
            SchedulePeriod.yearly: YearlySchedule
        }.get(self.period)

    @property
    def deposit_payment_scheduled_date(self):
        result = None if self.deposit_payment_date is None \
            else DepositsSchedule.objects.get(id=self.id).scheduled_date

        logger.debug("Schedule.deposit_payment_scheduled_date (id=%s, deposit_payment_date=%s, result=%s)"
                     % (self.id, self.deposit_payment_date, result))
        return result

    @property
    def first_payment_scheduled_date(self):
        result = self.schedule_cls_by_period.objects \
            .filter(id=self.id) \
            .order_by("scheduled_date") \
            .first().scheduled_date

        logger.debug("Schedule.first_payment_scheduled_date (id=%s, start_date=%s, result=%s)"
                     % (self.id, self.start_date, result))
        return result


class OnetimeSchedule(AbstractSchedule):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        managed = False  # disable automatic Django management of underlying DB table
        db_table = "frontend_api_one_time_schedule"

    def __str__(self):
        return "[%s, scheduled_date=%s, payment_account_id=%s]" % (
            super().__str__(), self.scheduled_date, self.payment_account_id
        )

    @property
    def origin_payment_account_id(self):
        return self.payment_account_id


class WeeklySchedule(AbstractSchedule):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        managed = False
        db_table = "frontend_api_weekly_schedule"

    def __str__(self):
        return "[%s, scheduled_date=%s, payment_account_id=%s]" % (
            super().__str__(), self.scheduled_date, self.payment_account_id
        )

    @property
    def origin_payment_account_id(self):
        return self.payment_account_id


class MonthlySchedule(AbstractSchedule):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        managed = False
        db_table = "frontend_api_monthly_schedule"

    def __str__(self):
        return "[%s, scheduled_date=%s, payment_account_id=%s]" % (
            super().__str__(), self.scheduled_date, self.payment_account_id
        )

    @property
    def origin_payment_account_id(self):
        return self.payment_account_id


class QuarterlySchedule(AbstractSchedule):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        managed = False
        db_table = "frontend_api_quarterly_schedule"

    def __str__(self):
        return "[%s, scheduled_date=%s, payment_account_id=%s]" % (
            super().__str__(), self.scheduled_date, self.payment_account_id
        )

    @property
    def origin_payment_account_id(self):
        return self.payment_account_id


class YearlySchedule(AbstractSchedule):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        managed = False
        db_table = "frontend_api_yearly_schedule"

    def __str__(self):
        return "[%s, scheduled_date=%s, payment_account_id=%s]" % (
            super().__str__(), self.scheduled_date, self.payment_account_id
        )

    @property
    def origin_payment_account_id(self):
        return self.payment_account_id


class DepositsSchedule(AbstractSchedule):
    """
    Special schedule to pay out deposit payments
    """
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        managed = False
        db_table = "frontend_api_deposits_schedule"

    def __str__(self):
        return "[%s, scheduled_date=%s, payment_account_id=%s]" % (
            super().__str__(), self.scheduled_date, self.payment_account_id
        )

    @property
    def origin_payment_account_id(self):
        return self.payment_account_id


class AbstractSchedulePayments(Model):
    """
    Special model to hold relationships between every payment made within specific Schedule
    """

    class Meta:
        abstract = True

    schedule = models.ForeignKey(
        Schedule,
        on_delete=models.DO_NOTHING,
        blank=False
    )
    payment_id = models.UUIDField(help_text=_("Original UUID from payment-api service"))
    parent_payment_id = models.UUIDField(
        help_text=_("In case of follow-up payments, this points to a preceding payment UUID "),
        null=True,
        blank=True,
        default=None
    )
    funding_source_id = models.UUIDField()
    payment_status = EnumField(PaymentStatusType)
    original_amount = models.PositiveIntegerField(
        help_text=_("Original payment amount for retry operations"),
        null=False,
        default=0
    )
    is_deposit = models.BooleanField(
        default=False,
        help_text=_('Indicates whether this payment is deposit'),
    )


class SchedulePayments(AbstractSchedulePayments):
    pass


class LastSchedulePayments(AbstractSchedulePayments):
    """
     Special view-based model to work with last payments according to payment chains (payment_id, parent_payment_id)
     """

    class Meta:
        managed = False
        db_table = "frontend_api_last_schedulepayments"


@dataclass
class PayeeDetails:
    id: str
    title: str
    type: EnumField(PayeeType)
    iban: str
    recipient_name: str
    recipient_email: str
    payment_account_id: models.UUIDField()


@dataclass
class FundingSourceDetails:
    id: str
    currency: EnumField(Currency)
    type: EnumField(FundingSourceType)
    payment_account_id: models.UUIDField()
