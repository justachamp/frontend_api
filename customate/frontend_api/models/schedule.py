import logging
import datetime
from typing import Union
import arrow

from cached_property import cached_property
from django.core.validators import RegexValidator
from enumfields import EnumField
from django.db import models
from django.db.models import Sum, Q
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from core.models import Model, User
from core.fields import Currency, PaymentStatusType, FundingSourceType, PayeeType, UserRole
from frontend_api.fields import SchedulePurpose, SchedulePeriod, ScheduleStatus, SchedulePaymentType
from customate.settings import CELERY_BEAT_SCHEDULE, PAYMENT_SYSTEM_CLOSING_TIME
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
    additional_information = models.CharField(
        max_length=250,
        blank=True,
        null=True,
        validators=[RegexValidator(
            regex=r'^([a-zA-Z0-9\/\-\?\:\.\+ ]*)$',
            message='Field contains forbidden characters'
        )])
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
        TODO: Rewrite to fully rely on actual data in SchedulePayment instead of date comparison
        :return:
        """
        # return self.number_of_payments_made > 0 # we can't rely on this field here, since there is
        # a case of long-running PENDING payments(days), which might corrupt our next_payment_date calculations
        now_date = arrow.utcnow().datetime.date()
        # We cannot just compare dates and ignore time. If start_date is current date
        # then scheduler's start time is important in fact
        result = now_date > self.start_date or (
                now_date == self.start_date and arrow.utcnow() > self._get_celery_processing_time()
        )
        # @NOTE we don't use "first_payment_scheduled_date" here, because result of this method is displayed in some way
        # to the customer in UI and we don't want to confuse him
        logger.debug("Schedule._did_we_send_first_payment (id=%s, result=%s)" % (self.id, result))
        return result

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
        next_payment_datetime = None
        # If we didn't make any payments yet then factor is 1 (which transforms into: next week, next month etc.)
        period_shift_factor = max(1, self.number_of_payments_made)

        if not (self.status in [ScheduleStatus.open] and self.number_of_payments_left != 0):
            next_payment_datetime = None
        elif self.period is SchedulePeriod.one_time or not self._did_we_send_first_payment():
            next_payment_datetime = arrow.get(self.start_date)
        elif self.period is SchedulePeriod.weekly:
            next_payment_datetime = arrow.get(self.start_date).replace(weeks=+period_shift_factor)
        elif self.period is SchedulePeriod.monthly:
            next_payment_datetime = arrow.get(self.start_date).replace(months=+period_shift_factor)
            # Note how JAN->FEB is handled in following example:
            # <Arrow [2019-01-31T11:58:11.459665+00:00]> -> <Arrow [2019-02-28T11:58:11.459665+00:00]>
        elif self.period is SchedulePeriod.quarterly:
            next_payment_datetime = arrow.get(self.start_date).replace(months=+(4 * period_shift_factor))
        elif self.period is SchedulePeriod.yearly:
            next_payment_datetime = arrow.get(self.start_date).replace(years=+period_shift_factor)

        result = next_payment_datetime.datetime.date() if next_payment_datetime else None
        logger.debug("Schedule.next_payment_date (id=%s, status=%s, result=%s)" % (self.id, self.status, result))
        return result

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
        logger.info("Updated schedule (id=%s) status=%s (was=%s)" % (self.id, status, old_status), extra={
            'schedule_id': self.id,
            'new_status': status,
            'old_status': old_status
        })

    @property
    def processing(self) -> bool:
        return self.is_processing

    @processing.setter
    def processing(self, value: bool):
        old_val = self.is_processing
        self.is_processing = value
        self.save(update_fields=["is_processing"])
        logger.info("Updated schedule (id=%s) is_processing=%s (was=%s)" % (self.id, value, old_val), extra={
            'schedule_id': self.id,
            'new_value': value,
            'old_value': old_val
        })

    @property
    def overdue(self) -> bool:
        return self.is_overdue

    @overdue.setter
    def overdue(self, value: bool):
        old_val = self.is_overdue
        self.is_overdue = value
        self.save(update_fields=["is_overdue"])
        logger.info("Updated schedule (id=%s) is_overdue=%s (was=%s)" % (self.id, value, old_val), extra={
            'schedule_id': self.id,
            'new_value': value,
            'old_value': old_val
        })

    def refresh_number_of_payments_made(self):
        """
        Update count of actual payments made in the DB
        :return:
        """
        old_number_of_payments_made = self.number_of_payments_made
        # get the list of last successful, regular payments
        self.number_of_payments_made = LastSchedulePayments.objects.filter(
            schedule_id=self.id,
            payment_status__in=[PaymentStatusType.SUCCESS],
            is_deposit=False
        ).count()
        self.save(update_fields=["number_of_payments_made"])
        logger.info("Updated schedule (id=%s) number_of_payments_made=%s (was=%s)"
                    % (self.id, self.number_of_payments_made, old_number_of_payments_made),
                    extra={
                        'schedule_id': self.id,
                        'new_value': self.number_of_payments_made,
                        'old_value': old_number_of_payments_made
                    })

    def update_status(self) -> ScheduleStatus:
        """
        Update Schedule's status based on aggregated info about all underlying payments (see SchedulePayment model).
        This is in fact, state machine. We could only migrate from one specific state into another.

        Possible Schedule statuses
          'open', there are some future planned payments and all past payments are successful
          'closed' there are NO future planned payments and all past payments are successful
          'stopped', regardless of underlying payments statuses schedule is stopped by user

        :return: new Schedule status
        :rtype: ScheduleStatus
        """
        logger.info("Updating schedule(id=%s) with current status=%s" % (self.id, self.status))

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

            # If we wasn't in overdue state before and have backup FS to retry with - don't mark schedule as overdue
            if not self.overdue and self.can_retry_with_backup_funding_source():
                logger.info("Don't mark schedule (id=%s, overdue=%s, status=%s) as overdue because we have to retry "
                            "with backup funding source (id=%s)"
                            % (self.id, self.overdue, self.status, self.backup_funding_source_id))
            else:
                logger.info("Mark schedule (id=%s) as overdue and return current status=%s" % (self.id, self.status))
                self.overdue = True

            return self.status

        # if we've gone so far, we're definitely not overdue anymore
        logger.info("Mark schedule(id=%s) as not overdue" % self.id)
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
        logger.info("Accepting schedule (id=%s, status=%s)" % (self.id, self.status), extra={
            'schedule_id': self.id,
            'status': self.status
        })
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
        logger.info("Schedule was successfully accepted (id=%s, payment_fee_amount=%s, deposit_fee_amount=%s, "
                    "funding_source_id=%s, funding_source_type=%s, backup_funding_source_id=%s, "
                    "backup_funding_source_type=%s, is_execution_date_limited=%s)"
                    % (self.id, self.payment_fee_amount, self.deposit_fee_amount, self.funding_source_id,
                       self.funding_source_type, self.backup_funding_source_id, self.backup_funding_source_type,
                       self.is_execution_date_limited),
                    extra={'schedule_id': self.id})

    def reject(self):
        logger.info("Rejecting schedule (id=%s, status=%s)" % (self.id, self.status), extra={
            'schedule_id': self.id,
            'status': self.status
        })

        # reject schedules in 'PENDING' status only
        if self.status != ScheduleStatus.pending:
            raise ValidationError(f'Cannot reject schedule with current status (status={self.status})')

        self.move_to_status(ScheduleStatus.rejected)

    @staticmethod
    def has_active_schedules_with_source(funding_source_id):
        result = Schedule.objects.filter(
            funding_source_id=funding_source_id,
            status__in=Schedule.ACTIVE_SCHEDULE_STATUSES
        ).exists()
        logger.debug("Schedule.has_active_schedules_with_source (funding_source_id=%s, result=%s)"
                     % (funding_source_id, result))
        return result

    @staticmethod
    def has_active_schedules_with_payee(payee_id):
        result = Schedule.objects.filter(
            payee_id=payee_id,
            status__in=Schedule.ACTIVE_SCHEDULE_STATUSES
        ).exists()
        logger.debug("Schedule.has_active_schedules_with_payee (payee_id=%s, result=%s)"
                     % (payee_id, result))
        return result

    @staticmethod
    def close_user_schedules(user_id):
        affected_rows_count = Schedule.objects.filter(Q(recipient_user__id=user_id) | Q(origin_user__id=user_id)) \
            .update(status=ScheduleStatus.closed)
        logger.info(f"Closed user's(id={user_id}) schedules (count={affected_rows_count})")

    @staticmethod
    def _get_celery_processing_time():
        st_hour = int(list(SCHEDULES_START_PROCESSING_TIME.hour)[0])
        st_minute = int(list(SCHEDULES_START_PROCESSING_TIME.minute)[0])
        return arrow.get("{full_date}T{hour}:{minute}:00".format(
            full_date=arrow.utcnow().format("YYYY-MM-DD"),
            hour=st_hour,
            minute=st_minute
        ), ['YYYY-MM-DDTH:mm:ss', 'YYYY-MM-DDTH:m:ss', 'YYYY-MM-DDTHH:m:ss'])

    @cached_property
    def have_time_for_nearest_payments_processing_by_scheduler(self):
        result = self.have_time_for_deposit_payment_processing_by_scheduler \
                 and self.have_time_for_regular_payment_processing_by_scheduler
        logger.info("Have %s time for nearest payments processing by scheduler (schedule_id=%s)"
                    % ('' if result else 'NO', self.id),
                    extra={'schedule_id': self.id})
        return result

    @cached_property
    def have_time_for_deposit_payment_processing_by_scheduler(self):
        if self.status is ScheduleStatus.pending:
            logger.info("Schedule is not accepted yet (id=%s). " % self.id,
                        extra={'schedule_id': self.id})
            return True

        if self.deposit_payment_date is None:
            logger.info("There is no deposit payment for schedule (id=%s)" % self.id,
                        extra={'schedule_id': self.id})
            return True

        have_made_deposit_payment = LastSchedulePayments.objects.filter(
            schedule_id=self.id,
            is_deposit=True
        ).exists()

        if have_made_deposit_payment:
            logger.info("Deposit payment for schedule (id=%s) was made already" % self.id,
                        extra={'schedule_id': self.id})
            return True

        deposit_payment = DepositsSchedule.objects.get(
            pk=self.id,
            status=ScheduleStatus.open.value
        )
        scheduled_date = arrow.get(deposit_payment.scheduled_date).datetime.date()
        nearest_scheduler_processing_date = self.nearest_scheduler_processing_date()
        result = scheduled_date >= nearest_scheduler_processing_date
        logger.info("Have %s time for deposit payment processing by scheduler (schedule_id=%s, scheduled_date=%s, "
                    "nearest_scheduler_processing_date=%s)"
                    % ('' if result else 'NO', self.id, scheduled_date, nearest_scheduler_processing_date),
                    extra={'schedule_id': self.id})
        return result

    @cached_property
    def have_time_for_regular_payment_processing_by_scheduler(self):
        if self.status is ScheduleStatus.pending:
            logger.info("Schedule is not accepted yet (id=%s). " % self.id,
                        extra={'schedule_id': self.id})
            return True

        number_of_sent_regular_payments = SchedulePayments.objects.filter(
            schedule_id=self.id,
            parent_payment_id=None,
            is_deposit=False
        ).count()

        if number_of_sent_regular_payments == self.number_of_payments:
            logger.info(
                "We sent all required regular payments for schedule (id=%s, number_of_sent_regular_payments=%s, number_of_payments=%s)"
                % (self.id, number_of_sent_regular_payments, self.number_of_payments),
                extra={'schedule_id': self.id})
            return True

        # Selecting nearest scheduled date for regular payments, by skipping dates for which
        # we already sent payments
        from_index = number_of_sent_regular_payments
        to_index = from_index + 1
        nearest_payment = self.periodic_class.objects.filter(
            id=self.id,
            status=ScheduleStatus.open,
        ).order_by("scheduled_date").all()[from_index:to_index].first()

        scheduled_date = arrow.get(nearest_payment.scheduled_date).datetime.date()
        nearest_scheduler_processing_date = self.nearest_scheduler_processing_date()
        result = scheduled_date >= nearest_scheduler_processing_date
        logger.info(
            "Have %s time for regular payment processing by scheduler (id=%s, scheduled_date=%s, nearest_scheduler_processing_date=%s)"
            % ('' if result else 'NO', self.id, scheduled_date, nearest_scheduler_processing_date),
            extra={'schedule_id': self.id})
        return result

    @cached_property
    def have_time_for_first_payments_processing_manually(self):
        result = Schedule.have_time_for_payment_processing_manually(
            self.deposit_payment_scheduled_date, self.is_execution_date_limited) \
                 or Schedule.have_time_for_payment_processing_manually(
            self.first_payment_scheduled_date, self.is_execution_date_limited)
        logger.info("Have %s time for first payments processing manually for schedule (id=%s)"
                    % ('' if result else 'NO', self.id),
                    extra={'schedule_id': self.id})
        return result

    @staticmethod
    def have_time_for_payment_processing_manually(payment_date, is_execution_date_limited):
        result = False
        utcnow = arrow.utcnow()

        if payment_date is None or (is_execution_date_limited and BlacklistDate.contains(utcnow.datetime.date())):
            logger.info(
                "Specified payment date (%s) is blacklisted, skipping verification for manual payment processing"
                % payment_date)
            return result

        current_day_start, current_day_end = utcnow.span('day')
        payment_time = arrow.get(payment_date).replace(hour=utcnow.hour, minute=utcnow.minute, second=utcnow.second)

        if is_execution_date_limited:
            ps_hour, ps_minute = PAYMENT_SYSTEM_CLOSING_TIME.split(':')
            ps_closing_time = utcnow.replace(hour=int(ps_hour), minute=int(ps_minute))
            result = current_day_start < payment_time < ps_closing_time
        else:
            # Payment API's closing time restriction can be ignored if we don't interact with bank
            result = current_day_start < payment_time < current_day_end

        logger.info("Have %s time for payment processing manually (payment_date=%s, is_execution_date_limited=%s)"
                    % ('' if result else 'NO', payment_date, is_execution_date_limited))
        return result

    def nearest_scheduler_processing_date(self):
        """
        Find out nearest schedulers processing time (taking into account blacklisted dates) for this schedule
        :return: datetime.date
        """
        scheduler_start_time = Schedule._get_celery_processing_time()
        retry_count = 1

        while True:
            if retry_count > BLACKLISTED_DAYS_MAX_RETRY_COUNT:
                logger.warning("Reached max retry count (%s) during scheduler processing date calculation. Stopping"
                               % BLACKLISTED_DAYS_MAX_RETRY_COUNT)
                break

            if (self.is_execution_date_limited and BlacklistDate.contains(scheduler_start_time.datetime.date())) \
                    or arrow.utcnow() > scheduler_start_time:
                logger.debug("Current scheduler start date (%s) is blacklisted or in the past. Trying with next day"
                             % scheduler_start_time)
                scheduler_start_time = scheduler_start_time.shift(days=1)
            else:
                break

        result = scheduler_start_time.datetime.date()
        logger.debug("Nearest scheduler processing date result: %s" % result)
        return result

    @property
    def periodic_class(self):
        return Schedule.get_periodic_class(self.period)

    @staticmethod
    def get_periodic_class(period: SchedulePeriod):
        return {
            SchedulePeriod.one_time: OnetimeSchedule,
            SchedulePeriod.weekly: WeeklySchedule,
            SchedulePeriod.monthly: MonthlySchedule,
            SchedulePeriod.quarterly: QuarterlySchedule,
            SchedulePeriod.yearly: YearlySchedule
        }.get(period)

    @cached_property
    def deposit_payment_scheduled_date(self):
        result = None if self.deposit_payment_date is None \
            else DepositsSchedule.objects.get(id=self.id).scheduled_date
        logger.debug("Schedule.deposit_payment_scheduled_date (id=%s, deposit_payment_date=%s, result=%s)" % (
            self.id, self.deposit_payment_date, result
        ))
        return result

    @cached_property
    def first_payment_scheduled_date(self):
        result = self.periodic_class.objects \
            .filter(id=self.id) \
            .order_by("scheduled_date") \
            .first().scheduled_date
        logger.debug("Schedule.first_payment_scheduled_date (id=%s, start_date=%s, result=%s)" % (
            self.id, self.start_date, result
        ))
        return result

    def can_retry_with_backup_funding_source(self):
        """
        This method assumes that it will query the latest schedule payment record, make sure that this is TRUE
        for concurrent environment (executing this method not in DB transaction scope may lead to issues)
        :return: bool
        """
        latest_schedule_payment = LastSchedulePayments.objects.filter(
            schedule_id=self.id
        ).order_by("-updated_at").first()

        logger.debug("latest_schedule_payment(id=%s, status=%s, funding_source_id=%s)" % (
            latest_schedule_payment.id,
            latest_schedule_payment.payment_status,
            latest_schedule_payment.funding_source_id
        ))
        # NOTE: check that we're being called after primary FS was already used(!)
        return latest_schedule_payment.payment_status in [PaymentStatusType.FAILED, PaymentStatusType.REFUND] \
               and self.backup_funding_source_id \
               and latest_schedule_payment.funding_source_id == self.funding_source_id

    @property
    def is_execution_date_limited(self):
        return self.funding_source_type is not FundingSourceType.WALLET or self.payee_type is not PayeeType.WALLET

    @staticmethod
    def is_execution_date_limited_filters(is_execution_date_limited: bool) -> Q:
        """
        Returns set of filters for use in Django ORM queries
        :param is_execution_date_limited: bool
        :return Q: complex lookup query
        """
        if is_execution_date_limited:
            return ~Q(funding_source_type=FundingSourceType.WALLET) | ~Q(payee_type=PayeeType.WALLET)
        else:
            return Q(funding_source_type=FundingSourceType.WALLET) & Q(payee_type=PayeeType.WALLET)

    def allow_post_document(self, user: User) -> bool:
        """
        :param user:
        :return:
        """
        recipient = self.recipient_user
        # Check if recipient or sender have common account with user from request (or user's subusers)
        related_account_ids = user.get_all_related_account_ids()

        # Check if schedule has status 'stopped'
        #    need to avoid documents handling for such schedules
        if self.status == ScheduleStatus.stopped:
            return False

        if user.role == UserRole.owner:
            return (recipient and recipient.account.id in related_account_ids) \
                   or self.origin_user.account.id in related_account_ids

        # Check if subuser from request is subuser of recipient or sender
        if user.role == UserRole.sub_user:
            return getattr(user.account.permission, "manage_schedules") and \
                   any([recipient == user.account.owner_account.user,
                        self.origin_user == user.account.owner_account.user,
                        self.origin_user == user])
        return False


class OnetimeSchedule(AbstractSchedule):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    original_scheduled_date = models.DateField()  # specific date w/o any weekends and blacklisted days
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
    original_scheduled_date = models.DateField()  # specific date w/o any weekends and blacklisted days
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
    original_scheduled_date = models.DateField()  # specific date w/o any weekends and blacklisted days
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
    original_scheduled_date = models.DateField()  # specific date w/o any weekends and blacklisted days
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
    original_scheduled_date = models.DateField()  # specific date w/o any weekends and blacklisted days
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


PeriodicSchedule = Union[
    OnetimeSchedule, WeeklySchedule, MonthlySchedule, QuarterlySchedule, YearlySchedule
]


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
    payment_id = models.UUIDField(
        help_text=_("Original UUID from payment-api service")
    )
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
    idempotence_key = models.UUIDField(
        default=None,
        null=True,
        help_text=_("used to avoid potential double charges when calling payment-api")
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
