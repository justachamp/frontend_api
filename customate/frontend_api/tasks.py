from __future__ import absolute_import, unicode_literals
from typing import Dict, Callable
from traceback import format_exc
import arrow
import logging
from uuid import UUID
from celery import shared_task
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from core.models import User
from core.fields import Currency, PaymentStatusType
from frontend_api.models import Schedule
from frontend_api.models.schedule import OnetimeSchedule, DepositsSchedule, AbstractSchedule
from frontend_api.models.schedule import WeeklySchedule, MonthlySchedule, QuarterlySchedule, YearlySchedule
from frontend_api.models.schedule import SchedulePayments, LastSchedulePayments
from frontend_api.core.client import PaymentApiClient, PaymentDetails
from frontend_api.fields import SchedulePurpose, ScheduleStatus

logger = logging.getLogger(__name__)
PER_PAGE = 5


# NOTE: make sure we use only primitive types in @shared_task signatures, otherwise there will be a need to write our own
# custom JSON serializer. For more details see here:
# https://stackoverflow.com/questions/53416726/can-i-use-dataclasses-or-similar-as-arguments-and-return-values-for-celery-tas
# https://stackoverflow.com/questions/21631878/celery-is-there-a-way-to-write-custom-json-encoder-decoder/

@shared_task
def make_payment(user_id: str, payment_account_id: str, schedule_id: str, currency: str, payment_amount: int,
                 additional_information: str, payee_id: str, funding_source_id: str, parent_payment_id=None):
    """
    Calls payment API to initiate a payment.

    :param user_id:
    :param payment_account_id:
    :param schedule_id:
    :param currency:
    :param payment_amount:
    :param additional_information:
    :param payee_id:
    :param funding_source_id:
    :param parent_payment_id: Parent payment to make sure we could trace retry-payment chains
    :return:
    """
    logger.info("make payment: user_id=%s, payment_account_id=%s, schedule_id=%s, currency=%s, payment_amount=%s, "
                "additional_information=%s, payee_id=%s, funding_source_id=%s, parent_payment_id=%s" % (
                    user_id, payment_account_id, schedule_id, currency, payment_amount,
                    additional_information, payee_id, funding_source_id, parent_payment_id
                ))

    try:
        PaymentApiClient.create_payment(p=PaymentDetails(
            user_id=UUID(user_id),
            payment_account_id=UUID(payment_account_id),
            schedule_id=UUID(schedule_id),
            currency=Currency(currency),
            amount=payment_amount,
            description=additional_information,
            payee_id=UUID(payee_id),
            funding_source_id=UUID(funding_source_id),
            parent_payment_id=UUID(parent_payment_id) if parent_payment_id else None
        ))
    except Exception as e:
        logger.error("Unable to create payment for schedule_id=%s: %r" % (schedule_id, format_exc()))
        Schedule.objects.get(id=schedule_id).move_to_status(ScheduleStatus.overdue)
        return


@shared_task
def on_payment_change(payment_info: Dict):
    """
    Process notification about changes in Payment model received from Payment-api.
    :param payment_info:
    :return:
    """
    payment_id = payment_info.get("payment_id")
    parent_payment_id = payment_info.get("parent_payment_id")
    schedule_id = payment_info.get("schedule_id")
    funding_source_id = payment_info.get("funding_source_id")
    payment_status = PaymentStatusType(payment_info.get('status'))
    amount = int(payment_info.get("amount"))

    logger.info("on_payment_change (payment_id=%s), payment_info=%r" % (payment_id, payment_info))

    if schedule_id is None:
        logger.info("Skipping payment_id=%s processing as it is not related to any schedule" % payment_id)
        return

    # some sanity checks
    try:
        schedule = Schedule.objects.get(id=schedule_id)  # type: Schedule
    except ObjectDoesNotExist:
        logger.error("Given schedule(id=%s) no longer exists, exiting" % schedule_id)
        return

    try:
        _ = User.objects.get(id=schedule.user_id)
    except ObjectDoesNotExist:
        logger.error("Given user(id=%s) no longer exists, exiting" % schedule.user_id)
        return

    try:
        # Save/update payment info into DB here, by avoiding duplicates using DB constraint on (schedule_id, payment_id)
        schedule_payment = SchedulePayments(
            schedule_id=schedule_id,
            payment_id=payment_id,
            funding_source_id=funding_source_id,
            parent_payment_id=parent_payment_id,
            payment_status=payment_status,
            original_amount=amount
        )
        schedule_payment.save()
        logger.info("Created new SchedulePayment(payment_id=%s, schedule_id=%s)" % (payment_id, schedule_id))

    except IntegrityError as e:
        if "frontend_api_schedulepayments_payment_id_schedule_id" in str(e):
            logger.info("SchedulePayment(payment_id=%s, schedule_id=%s) record already exists, updating status only" % (
                payment_id, schedule_id
            ))
            schedule_payment = SchedulePayments.objects.get(schedule_id=schedule_id, payment_id=payment_id)
            schedule_payment.payment_status = payment_status
            schedule_payment.save(update_fields=['payment_status'])
        else:
            logger.error("Got DB exception(payment_id=%s): %r " % (payment_id, format_exc()))

    # update Schedule status
    schedule.update_status()

    # Retry payment using backup funding source if it is available
    # NOTE: check that we're being called after primary FS was already used(!)
    if payment_status in [PaymentStatusType.FAILED, PaymentStatusType.REFUND] \
            and schedule.backup_funding_source_id \
            and funding_source_id == str(schedule.funding_source_id):
        logger.info("Retrying payment(id=%s, status=%s) using backup funding source(id=%s,was=%s)" % (
            payment_id, payment_status, schedule.backup_funding_source_id, funding_source_id
        ))
        make_payment.delay(
            user_id=str(schedule.user_id),
            payment_account_id=str(schedule.payment_account_id),
            schedule_id=str(schedule.id),
            currency=str(schedule.currency.value),
            payment_amount=amount,  # NOTE: use the same amount of original payment!
            additional_information=str(schedule.additional_information),
            payee_id=str(schedule.payee_id),
            funding_source_id=str(schedule.backup_funding_source_id),  # NOTE: This time, use backup funding source!
            parent_payment_id=payment_id  # NOTE: specify originating payment, to be able to track payment chains
        )
        return


@shared_task
def make_overdue_payment(schedule_id: str):
    """
    Tries to make follow-up payments based on last failed list of payments for specific schedule.
    :param schedule_id:
    :return:
    """
    logger.info("make_overdue_payment(schedule_id=%s)" % schedule_id)
    try:
        schedule = Schedule.objects.get(id=schedule_id)  # type: Schedule
    except Exception as e:
        logger.error("Unable to fetch schedule(id=%s) from DB: %r" % (
            schedule_id, format_exc()
        ))
        return

    if schedule.status is not ScheduleStatus.overdue:
        logger.error("Schedule(id=%s) expected status is not %s, got status=%s instead. Exiting" % (
            schedule_id, ScheduleStatus.overdue, schedule.status
        ))
        return

    # Select all SchedulePayments which are last in chains and are not in SUCCESS status
    overdue_payments = LastSchedulePayments.objects.filter(
        schedule_id=schedule_id,
        payment_status__in=[PaymentStatusType.FAILED, PaymentStatusType.REFUND]
    ).order_by("created_at")  # type: list[LastSchedulePayments]

    for op in overdue_payments:
        logger.info("SchedulePayment(id=%s, payment_id=%s, parent_payment_id=%s) is overdue, retrying payment." % (
            op.id, op.payment_id, op.parent_payment_id
        ))
        make_payment.delay(
            user_id=str(schedule.user_id),
            payment_account_id=str(schedule.payment_account_id),
            schedule_id=str(schedule_id),
            currency=str(schedule.currency.value),
            payment_amount=int(op.original_amount),  # NOTE: use original amount saved at the time of initial payment!
            additional_information=str(schedule.additional_information),
            payee_id=str(schedule.payee_id),
            funding_source_id=str(schedule.funding_source_id),  # NOTE: always retry using primary FS
            parent_payment_id=str(op.payment_id)  # NOTE: keep payment chain in order!
        )


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
            logger.info("Submit deposit payment, schedule_id=%s, user_id=%s, "
                        "payment_account_id=%s, deposit_payment_amount=%s, period=%s" % (
                            s.id, s.user_id, s.payment_account_id, s.deposit_amount, s.period
                        ))

            # submit task for asynchronous processing to queue
            make_payment.delay(
                user_id=str(s.user_id),
                payment_account_id=str(s.payment_account_id),
                schedule_id=str(s.id),
                currency=str(s.currency.value),
                payment_amount=int(s.deposit_amount),
                additional_information=str(s.additional_information),
                payee_id=str(s.payee_id),
                funding_source_id=str(s.funding_source_id)
            )


def submit_scheduled_payment(s: Schedule):
    """
    A common method to submit payments for execution
    :param s:
    :return:
    """
    logger.debug("Submit regular payment. schedule_id=%s, user_id=%s, payment_account_id=%s, "
                 "payment_amount=%s, deposit_payment_amount=%s, period=%s" % (
                     s.id, s.user_id, s.payment_account_id, s.payment_amount, s.deposit_amount, s.period
                 ))

    # submit task for asynchronous processing to queue
    make_payment.delay(
        user_id=str(s.user_id),
        payment_account_id=str(s.payment_account_id),
        schedule_id=str(s.id),
        currency=str(s.currency.value),
        payment_amount=int(s.payment_amount),
        additional_information=str(s.additional_information),
        payee_id=str(s.payee_id),
        funding_source_id=str(s.funding_source_id)
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
            submit_scheduled_payment(s)


def process_all_weekly_payments(scheduled_date):
    """
    Process all weekly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = WeeklySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=[ScheduleStatus.open, ScheduleStatus.overdue],
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s)


def process_all_monthly_payments(scheduled_date):
    """
    Process all monthly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = MonthlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=[ScheduleStatus.open, ScheduleStatus.overdue],
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s)


def process_all_quarterly_payments(scheduled_date):
    """
    Process all quarterly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = QuarterlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=[ScheduleStatus.open, ScheduleStatus.overdue],
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s)


def process_all_yearly_payments(scheduled_date):
    """
    Process all yearly payments for specified date
    :param scheduled_date:
    :return:
    """
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = YearlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=[ScheduleStatus.open, ScheduleStatus.overdue],
        purpose=SchedulePurpose.pay
    ).order_by("created_at")
    paginator = Paginator(payments, PER_PAGE)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s)


@shared_task
def initiate_daily_payments():
    """
    Initial entry point task which iterates through all Schedules and initiates payment tasks if dates match.

    :return:
    """

    # get current date
    now = arrow.utcnow().datetime

    # TODO: skip weekends and custom blacklisted dates from DB
    # TODO: implement Future-date lookups to check wether we should process them right now,
    # because they are blacklisted and/or weekends

    # process deposit payments first
    process_all_deposit_payments(now)
    process_all_one_time_payments(now)
    process_all_weekly_payments(now)
    process_all_monthly_payments(now)
    process_all_quarterly_payments(now)
    process_all_yearly_payments(now)


@shared_task
def on_payee_change(payee_info: Dict):
    """
    Process notification about changes in Payee model received from Payment-api.
    :param payee_info:
    :return:
    """
    pass
    # TODO: update all payee info that is stored in Django models
