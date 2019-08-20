import logging
import datetime
import arrow
from dataclasses import dataclass
from enumfields import EnumField
from django.db import models
from django.utils.translation import gettext_lazy as _
from core.models import Model, User
from core.fields import Currency, PaymentStatusType, FundingSourceType, PayeeType
from rest_framework.serializers import ValidationError
from frontend_api.fields import SchedulePurpose, SchedulePeriod, ScheduleStatus, SchedulePaymentType, \
    SchedulePaymentInitiator

logger = logging.getLogger(__name__)


class Schedule(Model):
    name = models.CharField(_('schedule name'), max_length=150)
    status = EnumField(ScheduleStatus)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=False
    )
    purpose = EnumField(SchedulePurpose)
    currency = EnumField(Currency)
    payee_id = models.UUIDField(help_text=_("Money recipient"))
    payee_title = models.CharField(max_length=100, default='')
    payee_recipient_name = models.CharField(max_length=254, default='')
    payee_recipient_email = models.CharField(max_length=254, default='')
    payee_iban = models.CharField(max_length=50, default='')
    funding_source_id = models.UUIDField()
    backup_funding_source_id = models.UUIDField(default=None, blank=True, null=True)
    period = EnumField(SchedulePeriod)
    number_of_payments = models.PositiveIntegerField(
        default=0, help_text=_("Initial number of payments in the current schedule set upon creation.")
    )
    number_of_payments_left = models.PositiveIntegerField(
        default=0, help_text=_("Number of payments left in the current schedule. Changes dynamically in time")
    )
    start_date = models.DateField()
    payment_amount = models.PositiveIntegerField()
    fee_amount = models.PositiveIntegerField(
        default=0, help_text=_("Approximate fee amount for all payments (including deposit) in schedule")
    )
    deposit_amount = models.PositiveIntegerField(
        null=True, help_text=_("Initial payment independent of the rest of scheduled payments")
    )
    deposit_payment_date = models.DateField(null=True)  # This should be strictly < start_date
    additional_information = models.CharField(max_length=250, blank=True, null=True)
    total_paid_sum = models.PositiveIntegerField(
        default=0,
        help_text=_("Total sum of all Schedule's paid payments")
    )
    total_sum_to_pay = models.PositiveIntegerField(
        default=0,
        help_text=_("Total sum that should be paid by this schedule")
    )

    def save(self, *args, **kwargs):
        """
        Pre-calculate some fields in this overridden method.
        :param args:
        :param kwargs:
        :return:
        """
        # this should be the same at the beginning
        self.number_of_payments_left = self.number_of_payments
        self._calculate_and_set_total_sum_to_pay()
        super().save(*args, **kwargs)

    def _calculate_and_set_total_sum_to_pay(self):
        self.total_sum_to_pay = self.fee_amount \
                                + (self.deposit_amount if self.deposit_amount is not None else 0) \
                                + (self.payment_amount * self.number_of_payments_left)

    def is_cancelable(self):
        return self.status in [ScheduleStatus.open, ScheduleStatus.overdue]

    def _did_we_make_first_payment(self):
        # NOTE: don't think that we can rely on total_paid_sum field instead (considering long running transactions)
        return arrow.utcnow().datetime.date() > self.start_date

    @property
    def next_payment_date(self):
        """
        TODO: Calculate next payment date, according to weekends and custom holidays in separate table (TBD)
        TODO2: Take into account last_payment_date (instead of start_date)
        :return:
        :rtype: datetime.date|None
        """
        res = None

        if not (self.status in [ScheduleStatus.open, ScheduleStatus.overdue] and self.number_of_payments_left != 0):
            res = None
        elif self.period is SchedulePeriod.one_time or not self._did_we_make_first_payment():
            res = arrow.get(self.start_date)
        elif self.period is SchedulePeriod.weekly:
            res = arrow.get(self.start_date).replace(weeks=+1)
        elif self.period is SchedulePeriod.monthly:
            res = arrow.get(self.start_date).replace(months=+1)
            # Note how JAN->FEB is handled in following example:
            # <Arrow [2019-01-31T11:58:11.459665+00:00]> -> <Arrow [2019-02-28T11:58:11.459665+00:00]>
        elif self.period is SchedulePeriod.quarterly:
            res = arrow.get(self.start_date).replace(months=+4)
        elif self.period is SchedulePeriod.yearly:
            res = arrow.get(self.start_date).replace(years=+1)

        return res.datetime.date() if res else None

    @property
    def payment_type(self):
        """
        Returns schedule payment type. Helpful for the client to be able to calculate different fees when selecting
        funding source(s)
        TODO: Implement correct payment_type detection and return valid value for client
        :return:
        """
        return str(SchedulePaymentType.external.value)

    def pay_overdue(self, payment_client):
        if self.status != ScheduleStatus.overdue:
            raise ValidationError(f'Cannot process overdue payments for schedule ({self.id})')

        if self._process_overdue_payments(self._get_schedules_with_overdue_payments(), payment_client):
            self.move_to_status(ScheduleStatus.open)

    def _get_schedules_with_overdue_payments(self):
        min_funding_source_priority = 1
        query = (
            'select * ',
            'from ' + SchedulePayments.objects.model._meta.db_table,
            'where ',
            ' schedule_id = %(schedule_id)s',
            ' and initiator = %(initiator)s',
            ' and funding_source_priority = %(min_funding_source_priority)s',
            ' and iteration_number not in (select distinct iteration_number',
            'from ' + SchedulePayments.objects.model._meta.db_table,
            'where',
            'payment_status not in %(payment_statuses)s',
            'and schedule_id = %(schedule_id)s);'
        )

        return SchedulePayments.objects.raw(query, {
            'schedule_id': self.id,
            'initiator': SchedulePaymentInitiator.schedule,
            'min_funding_source_priority': min_funding_source_priority,
            'payment_statuses': [PaymentStatusType.FAILED, PaymentStatusType.REFUND, PaymentStatusType.CANCELED]
        })

    def _process_overdue_payments(self, schedules_with_overdue_payments, payment_client):
        result = True

        for schedule_with_payment in schedules_with_overdue_payments:
            original_payment_id = schedule_with_payment.payment_id
            forced_payment = self._force_overdue_payment(original_payment_id, payment_client)

            if forced_payment is None:
                raise ValidationError(f'Cannot force overdue payment ({original_payment_id})')

            SchedulePayments.log_schedule_with_forced_payment(schedule_with_payment, forced_payment)

            if forced_payment.new_payment_status == PaymentStatusType.FAILED:
                result = False
                break

        return result

    # def _force_overdue_payment(self, payment_id: str, payment_client):
    #     return payment_client.force_payment(payment_id)

    def move_to_status(self, status: ScheduleStatus):
        self.status = status
        self.save(update_fields=["status"])

    def update_status(self) -> ScheduleStatus:
        """
        Update Schedule's status based on aggregated info about all underlying payments (see SchedulePayments model).
        This is in fact, state machine. We could only migrate from one specific state into another.
        TODO: Lookup scheduler diagram by Oleg to better understand what statuses we should update based on what conditions

        :return: new Schedule status
        :rtype: ScheduleStatus
        """
        original_status = self.status
        logger.debug("Updating schedule(id=%s) status(%s)" % (self.id, self.status))
        new_status = ScheduleStatus.open

        # Possible Schedule statuses
        # 'open', there are some future planned payments and all past payments are successful
        # 'closed' there are NO future planned payments and all past payments are successful
        # 'overdue', there are some past payments which were unsuccessful
        # 'cancelled', regardless of underlying payments statuses schedule is cancelled by user
        # 'processing', there is at least ONE payment which status is 'PROCESSING'

        # if self.status is ScheduleStatus.cancelled:
        #     result = ScheduleStatus.cancelled
        # elif PaymentStatusType.is_failed(payment_status):
        #     # @NOTE: we don't have backup source for now, so this condition should be enough
        #     result = ScheduleStatus.overdue
        # elif payment_status is PaymentStatusType.SUCCESS and self.number_of_payments_left == 0:
        #     result = ScheduleStatus.closed

        # TODO: Select all SchedulePayments
        schedule_payments = SchedulePayments.objects.filter(
            schedule_id=self.id,
            payment_status=PaymentStatusType.PROCESSING
        )

        logger.debug("Updated Schedule(id=%s) status=%s(was=%s)" % (self.id, new_status, original_status))
        self.status = new_status
        self.save(update_fields=["status"])
        return new_status

    def reduce_number_of_payments_left(self):
        if self.number_of_payments_left <= 0:
            return
        self.number_of_payments_left -= 1
        logger.debug("Reduced number_of_payments_left=%s (schedule_id=%s)" % (self.number_of_payments_left, self.id))
        self.save(update_fields=["number_of_payments_left"])

    @staticmethod
    def has_active_schedules_with_source(funding_source_id):
        statuses = [ScheduleStatus.open, ScheduleStatus.pending, ScheduleStatus.processing, ScheduleStatus.overdue]

        return Schedule.objects.filter(
            funding_source_id=funding_source_id,
            status__in=statuses
        ).exists()


class ScheduleCommonFieldsMixin(Model):
    scheduled_date = models.DateField()  # specific date on which the payment should be initiated
    payment_account_id = models.UUIDField(help_text=_("Account id issued by payment API during registration"))

    class Meta:
        # https://stackoverflow.com/questions/3254436/django-model-mixins-inherit-from-models-model-or-from-object
        abstract = True

    name = models.CharField(_('schedule name'), max_length=150)
    status = EnumField(ScheduleStatus)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        blank=False
    )
    purpose = EnumField(SchedulePurpose)
    currency = EnumField(Currency)
    payee_id = models.UUIDField(help_text=_("Money recipient"))
    payee_title = models.CharField(max_length=100, default='')
    payee_recipient_name = models.CharField(max_length=254, default='')
    payee_recipient_email = models.CharField(max_length=254, default='')
    payee_iban = models.CharField(max_length=50, default='')
    funding_source_id = models.UUIDField()
    backup_funding_source_id = models.UUIDField(default=None, blank=True, null=True)
    period = EnumField(SchedulePeriod)
    number_of_payments = models.PositiveIntegerField(
        default=0, help_text=_("Initial number of payments in the current schedule set upon creation.")
    )
    number_of_payments_left = models.PositiveIntegerField(
        default=0, help_text=_("Number of payments left in the current schedule. Changes dynamically in time")
    )
    start_date = models.DateField()
    payment_amount = models.PositiveIntegerField()
    fee_amount = models.PositiveIntegerField(
        default=0, help_text=_("Approximate fee amount for all payments (including deposit) in schedule")
    )
    deposit_amount = models.PositiveIntegerField(
        null=True, help_text=_("Initial payment independent of the rest of scheduled payments")
    )
    deposit_payment_date = models.DateField(null=True)  # This should be strictly < start_date
    additional_information = models.CharField(max_length=250, blank=True, null=True)


class OnetimeSchedule(ScheduleCommonFieldsMixin):
    class Meta:
        managed = False  # disable automatic Django management of underlying DB table
        db_table = "frontend_api_one_time_schedule"


class WeeklySchedule(ScheduleCommonFieldsMixin):
    class Meta:
        # see more at: https://resources.rescale.com/using-database-views-in-django-orm/
        managed = False
        db_table = "frontend_api_weekly_schedule"


class MonthlySchedule(ScheduleCommonFieldsMixin):
    class Meta:
        managed = False
        db_table = "frontend_api_monthly_schedule"


class QuarterlySchedule(ScheduleCommonFieldsMixin):
    class Meta:
        managed = False
        db_table = "frontend_api_quarterly_schedule"


class YearlySchedule(ScheduleCommonFieldsMixin):
    class Meta:
        managed = False
        db_table = "frontend_api_yearly_schedule"


class DepositsSchedule(ScheduleCommonFieldsMixin):
    """
    Special schedule to pay out deposit payments
    """

    class Meta:
        managed = False
        db_table = "frontend_api_deposits_schedule"


class SchedulePayments(Model):
    """
    Special model to hold relationships between every payment made within specific Schedule

    """
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

    @staticmethod
    def log_schedule_payment(schedule, payment, iteration_number: int):
        record = SchedulePayments(
            schedule=schedule,
            payment_id=payment.id,
            funding_source_id=schedule.funding_source_id,
            original_payment_id=None,
            payment_status=payment.status
        )
        record.save()

    @staticmethod
    def log_schedule_backup_payment(schedule, payment, iteration_number: int):
        record = SchedulePayments(
            schedule=schedule,
            payment_id=payment.id,
            funding_source_id=schedule.funding_source_id,
            original_payment_id=None,
            payment_status=payment.status
        )
        record.save()

    @staticmethod
    def log_schedule_with_forced_payment(schedule_with_payment, forced_payment):
        record = SchedulePayments(
            schedule=schedule_with_payment.schedule,
            payment_id=forced_payment.new_payment_id,
            # NOTE: or should we use new_payment.origin.id?
            funding_source_id=schedule_with_payment.funding_source_id,
            funding_source_priority=schedule_with_payment.funding_source_priority,
            original_payment_id=schedule_with_payment.payment_id,
            payment_status=forced_payment.new_payment_status
        )
        record.save()


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
