from __future__ import absolute_import, unicode_literals
import logging
from celery import shared_task
import arrow
from django.core.paginator import Paginator
from frontend_api.models import Schedule
from frontend_api.models.schedule import OnetimeSchedule, DepositsSchedule
from frontend_api.models.schedule import WeeklySchedule, MonthlySchedule, QuarterlySchedule, YearlySchedule

from frontend_api.fields import SchedulePurpose, SchedulePeriod, ScheduleStatus

logger = logging.getLogger(__name__)
PER_PAGE = 5


# @shared_task
# def add(x, y):
#     return x + y
#



@shared_task
def make_deposit_payment(schedule_id: str, user_id: str, payment_account_id: str, payee_id: str,
                         payment_amount: int, number_of_payments_left: int):
    #TODO: call external payment API here
    pass


@shared_task
def make_regular_payment(schedule_id: str, user_id: str, payment_account_id: str, payee_id: str,
                         payment_amount: int, number_of_payments_left: int, period: SchedulePeriod):
    pass


def process_all_deposit_payments(scheduled_date):
    """
    Process all deposit payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = DepositsSchedule.objects.filter(
        scheduled_date=scheduled_date,
        status=ScheduleStatus.open,
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: DepositsSchedule
            logger.debug("id=%s, user_id=%s, payment_account_id=%s, payment_amount=%s, payments_left=%s" % (
                s.id, s.user_id, s.payment_account_id, s.payment_amount, s.number_of_payments_left
            ))
            # submit task for asynchronous processing to queue
            make_deposit_payment.delay(
                schedule_id=str(s.id),
                user_id=str(s.user),
                payment_account_id=str(s.payment_account_id),
                payee_id=str(s.payee_id),
                payment_amount=s.payment_amount,
                number_of_payments_left=s.number_of_payments_left
            )


def process_all_one_time_payments(scheduled_date):
    """
    Process all one-time payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = OnetimeSchedule.objects.filter(
        scheduled_date=scheduled_date,
        status=ScheduleStatus.open,
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: OnetimeSchedule
            logger.debug("id=%s, user_id=%s, payment_account_id=%s, payment_amount=%s, payments_left=%s, period=%s" % (
                s.id, s.user_id, s.payment_account_id, s.payment_amount, s.number_of_payments_left, s.period
            ))
            # submit task for asynchronous processing to queue
            make_regular_payment.delay(
                schedule_id=str(s.id),
                user_id=str(s.user),
                payment_account_id=str(s.payment_account_id),
                payee_id=str(s.payee_id),
                payment_amount=s.payment_amount,
                number_of_payments_left=s.number_of_payments_left,
                period=s.period
            )




def process_all_weekly_payments(scheduled_date):
    """
    Process all weekly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = WeeklySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status=ScheduleStatus.open,
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: WeeklySchedule
            logger.debug("id=%s, user_id=%s, payment_account_id=%s, payment_amount=%s, payments_left=%s, period=%s" % (
                s.id, s.user_id, s.payment_account_id, s.payment_amount, s.number_of_payments_left, s.period
            ))
            # TODO: make_regular_payment.delay()


def process_all_monthly_payments(scheduled_date):
    """
    Process all monthly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = MonthlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status=ScheduleStatus.open,
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: MonthlySchedule
            logger.debug("id=%s, user_id=%s, payment_account_id=%s, payment_amount=%s, payments_left=%s, period=%s" % (
                s.id, s.user_id, s.payment_account_id, s.payment_amount, s.number_of_payments_left, s.period
            ))
            # TODO: make_regular_payment.delay()


def process_all_quarterly_payments(scheduled_date):
    """
    Process all quarterly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = QuarterlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status=ScheduleStatus.open,
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: QuarterlySchedule
            logger.debug("id=%s, user_id=%s, payment_account_id=%s, payment_amount=%s, payments_left=%s, period=%s" % (
                s.id, s.user_id, s.payment_account_id, s.payment_amount, s.number_of_payments_left, s.period
            ))
            # TODO: make_regular_payment.delay()


def process_all_yearly_payments(scheduled_date):
    """
    Process all yearly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = YearlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status=ScheduleStatus.open,
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: YearlySchedule
            logger.debug("id=%s, user_id=%s, payment_account_id=%s, payment_amount=%s, payments_left=%s, period=%s" % (
                s.id, s.user_id, s.payment_account_id, s.payment_amount, s.number_of_payments_left, s.period
            ))
            # TODO: make_regular_payment.delay()


@shared_task
def initiate_daily_payments():
    """
    Initial entry point task which iterates through all Schedules and initiates payment tasks if dates match.

    :return:
    """

    # get current date
    now = arrow.utcnow().datetime

    #TODO: skip weekends and custom blacklisted dates from DB

    # process deposit payments first
    process_all_deposit_payments(now)
    process_all_one_time_payments(now)
    process_all_weekly_payments(now)
    process_all_monthly_payments(now)
    process_all_quarterly_payments(now)
    process_all_monthly_payments(now)
