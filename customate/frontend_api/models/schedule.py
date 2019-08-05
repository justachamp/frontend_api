import datetime
import arrow
from dataclasses import dataclass
from enumfields import EnumField
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Model, User
from core.fields import Currency

from frontend_api.fields import SchedulePurpose, SchedulePeriod, ScheduleStatus


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
    period = EnumField(SchedulePeriod)
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

    # class Meta:
    #     ordering = ['-created_at']

    def __init__(self, *args, **kwargs):
        self._fee_amount = 0  # We accept this value from UI, but don't store it in database
        super().__init__(*args, **kwargs)

    def calculate_and_set_total_sum_to_pay(self):
        self.total_sum_to_pay = self.fee_amount \
                                + (self.deposit_amount if self.deposit_amount is not None else 0) \
                                + (self.payment_amount * self.number_of_payments_left)

    def is_cancelable(self):
        return self.status in [ScheduleStatus.open, ScheduleStatus.overdue]

    def _can_have_next_payment(self):
        return self.status in [ScheduleStatus.open, ScheduleStatus.overdue] \
               and self.number_of_payments_left != 0

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

        if not self._can_have_next_payment():
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
    period = EnumField(SchedulePeriod)
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



@dataclass
class SchedulePaymentsDetails:
    id: str
    total_paid_sum: int


@dataclass
class PayeeDetails:
    id: str
    title: str
    iban: str
    recipient_name: str
    recipient_email: str
