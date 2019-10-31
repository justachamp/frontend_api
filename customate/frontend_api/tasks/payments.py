from __future__ import absolute_import, unicode_literals
from typing import Dict
from traceback import format_exc
import logging

from uuid import UUID, uuid4
from celery import shared_task
import arrow
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.conf import settings
from django.db import transaction

from core.logger import RequestIdGenerator
from core.models import User
from core.fields import Currency, PaymentStatusType, TransactionStatusType
from frontend_api.models import Schedule
from frontend_api.models.blacklist import BlacklistDate, BLACKLISTED_DAYS_MAX_RETRY_COUNT
from frontend_api.models.schedule import OnetimeSchedule, DepositsSchedule
from frontend_api.models.schedule import WeeklySchedule, MonthlySchedule, QuarterlySchedule, YearlySchedule
from frontend_api.models.schedule import SchedulePayments, LastSchedulePayments
from frontend_api.core import client
from frontend_api.fields import ScheduleStatus
from frontend_api import helpers

logger = logging.getLogger(__name__)


# NOTE: make sure we use only primitive types in @shared_task signatures, otherwise there will be a need to write our own
# custom JSON serializer. For more details see here:
# https://stackoverflow.com/questions/53416726/can-i-use-dataclasses-or-similar-as-arguments-and-return-values-for-celery-tas
# https://stackoverflow.com/questions/21631878/celery-is-there-a-way-to-write-custom-json-encoder-decoder/

@shared_task
def make_failed_payment(user_id: str, payment_account_id: str, schedule_id: str, currency: str, payment_amount: int,
                 additional_information: str, payee_id: str, funding_source_id: str,
                 request_id=None, is_deposit=False):
    """
    Intentionally create failed payment to keep payment chains in order.
    This is required for further processing of overdue payments.

    :param user_id:
    :param payment_account_id:
    :param schedule_id:
    :param currency:
    :param payment_amount:
    :param additional_information:
    :param payee_id:
    :param funding_source_id:
    :param parent_payment_id:
    :param request_id:
    :param is_deposit:
    :return:
    """
    # We intentionally will send execution_date in past, so that these payments fail
    execution_date = arrow.utcnow().replace(years=-1).datetime
    return make_payment(
        user_id=user_id,
        payment_account_id=payment_account_id,
        schedule_id=schedule_id,
        currency=currency,
        payment_amount=payment_amount,
        additional_information=additional_information,
        payee_id=payee_id,
        funding_source_id=funding_source_id,
        is_deposit=is_deposit,
        request_id=request_id,
        execution_date=execution_date
    )


# Must NOT be executed in transaction, in this way we guarantee that SchedulePayments will be created event if something
# goes wrong after that. SchedulePayments record will eventually prevent making extra requests to PaymentApi
# upon second run for the same payment.
@shared_task
def make_payment(user_id: str, payment_account_id: str, schedule_id: str, currency: str, payment_amount: int,
                 additional_information: str, payee_id: str, funding_source_id: str, parent_payment_id=None,
                 execution_date=None, request_id=None, is_deposit=False):
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
    :param execution_date: When payment should be executed
    :param request_id: Unique processing request's id.
    :param is_deposit: Indicates whether this payment is deposit
    :return: created payment instance
    """
    logging.init_shared_extra(request_id)
    payment_id = uuid4()
    logger.info("Making payment: payment_id=%s, user_id=%s, payment_account_id=%s, schedule_id=%s, currency=%s, "
                "payment_amount=%s, additional_information=%s, payee_id=%s, funding_source_id=%s, parent_payment_id=%s,"
                " execution_date=%s, request_id=%s" % (
                    payment_id, user_id, payment_account_id, schedule_id, currency, payment_amount,
                    additional_information, payee_id, funding_source_id, parent_payment_id,
                    execution_date, request_id
                ),
                extra={
                    'schedule_id': schedule_id,
                    'payment_id': payment_id,
                    'funding_source_id': funding_source_id,
                    'payment_amount': payment_amount,
                    'is_deposit': is_deposit,
                })

    result = None

    try:
        schedule_payment = SchedulePayments(
            schedule_id=schedule_id,
            payment_id=payment_id,
            funding_source_id=funding_source_id,
            parent_payment_id=parent_payment_id,
            payment_status=PaymentStatusType.PENDING,
            original_amount=payment_amount,
            is_deposit=is_deposit
        )
        schedule_payment.save()
        logger.info("Schedule payment successfully created (schedule_id=%s, payment_id=%s)" % (schedule_id, payment_id))
    except Exception:
        logger.error("Saving schedule_payment record failed due to: %r" % format_exc(), extra={
            'schedule_id': schedule_id,
        })
        return result

    logger.info("Schedule payment record was created (id=%r)" % schedule_payment.id, extra={
        'schedule_payment_id': schedule_payment.id
    })

    try:
        result = client.PaymentApiClient.create_payment(p=client.PaymentDetails(
            id=payment_id,
            user_id=UUID(user_id),
            payment_account_id=UUID(payment_account_id),
            schedule_id=UUID(schedule_id),
            currency=Currency(currency),
            amount=payment_amount,
            description=additional_information,
            payee_id=UUID(payee_id),
            funding_source_id=UUID(funding_source_id),
            parent_payment_id=UUID(parent_payment_id) if parent_payment_id else None,
            execution_date=arrow.get(execution_date).datetime if execution_date else None
        ))
    except Exception:
        logger.error("Unable to create payment(id=%s) for schedule (id=%s) due to unknown error: %r. " % (
            payment_id, schedule_id, format_exc()
        ), extra={
            'schedule_id': schedule_id,
            'payment_id': payment_id
        })

        # We don't check or run payment with backup source here, because we have a severe problem that probably
        # will prevent next payment's successful execution
        schedule_payment.payment_status = PaymentStatusType.FAILED
        logger.info("Marking schedule payment (id=%s) as FAILED" % schedule_payment.id, extra={
            'schedule_payment_id': schedule_payment.id,
            'schedule_id': schedule_id,
            'payment_id': payment_id
        })

        schedule_payment.save(update_fields=['payment_status'])
        # move overall schedule to 'Overdue' status immediately
        Schedule.objects.get(id=schedule_id).move_to_status(ScheduleStatus.overdue)

    finally:
        return result


@shared_task
@transaction.atomic
def on_transaction_change(transaction_info: Dict):
    """
    Process notifications for incoming and outgoing transactions.
    :param transaction_info:
    :return:
    """
    logger.info("Start on_transaction_change. Transaction info: %s." % transaction_info)
    user_id = transaction_info.get("user_id")
    schedule_id = transaction_info.get("schedule_id")
    transaction_status = TransactionStatusType(transaction_info.get("status"))

    if not schedule_id:
        helpers.notify_about_loaded_funds(
            user_id=user_id,
            transaction_info=transaction_info,
            transaction_status=transaction_status)
        return

    try:
        schedule = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        logger.error("Schedule with id %s was not found. %r" % (schedule_id, format_exc()))
        return

    if transaction_status is TransactionStatusType.SUCCESS:
        helpers.notify_about_schedules_successful_payment(schedule=schedule, transaction_info=transaction_info)

    if transaction_status is TransactionStatusType.FAILED:
        helpers.notify_about_schedules_failed_payment(schedule=schedule, transaction_info=transaction_info)


@shared_task
@transaction.atomic
def on_payment_change(payment_info: Dict):
    """
    Process notification about changes in Payment model received from Payment-api.
    :param payment_info:
    :return:
    """
    payment_id = payment_info.get("payment_id")
    payment_account_id = payment_info.get("account_id")
    schedule_id = payment_info.get("schedule_id")
    funding_source_id = payment_info.get("funding_source_id")
    payment_status = PaymentStatusType(payment_info.get('status'))
    amount = int(payment_info.get("amount"))
    request_id = payment_info.get("request_id", RequestIdGenerator.get())

    logging.init_shared_extra(request_id)
    logger.info("Received 'payment changed' event, starting processing (payment_id=%s, payment_info=%r)" % (
        payment_id, payment_info
    ), extra={
        'request_id': request_id,
        'payment_id': payment_id,
        'schedule_id': schedule_id,
        'funding_source_id': funding_source_id,
        'payment_status': payment_status
    })

    if schedule_id is None:
        logger.info("Skipping payment (id=%s), not related to any schedule" % payment_id, extra={
            'request_id': request_id,
            'payment_id': payment_id
        })
        return

    # some sanity checks
    try:
        schedule = Schedule.objects.get(id=schedule_id)  # type: Schedule
    except ObjectDoesNotExist:
        logger.error("Given schedule (id=%s) no longer exists, exiting" % schedule_id, extra={
            'schedule_id': schedule_id
        })
        return

    # TODO: need to elaborate more on what is happening here. Very unclear
    # We set "scheduleId" for payments which created with link to origin user *and* for "incoming" payments
    # which are created for recipient user, but processing such events for recipient's payment could lead to confusion
    # and break our logic with "number_of_payment_*" fields
    if str(schedule.origin_payment_account_id) != payment_account_id:
        logger.info("Skipping payment (id=%s), not related to schedule\'s payer(origin_payment_account_id=%s)" % (
            payment_id, schedule.origin_payment_account_id
        ), extra={
            'payment_id': payment_id,
            'schedule_id': schedule_id,
            'schedule.origin_payment_account_id': schedule.origin_payment_account_id,
            'payment_account_id': payment_account_id
        })
        return

    try:
        User.objects.get(id=schedule.origin_user_id)
    except ObjectDoesNotExist:
        logger.error("Given user (id=%s) no longer exists, exiting" % schedule.origin_user_id, extra={
            'payment_id': payment_id,
            'schedule_id': schedule_id,
            'schedule.origin_user_id': schedule.origin_user_id
        })
        return

    schedule_payment = SchedulePayments.objects.get(schedule_id=schedule_id, payment_id=payment_id)
    schedule_payment.payment_status = payment_status
    schedule_payment.save(update_fields=['payment_status'])

    # refresh actual count of payments for specific schedule
    if payment_status is PaymentStatusType.SUCCESS:
        schedule.refresh_number_of_payments_made()

    # update Schedule status
    schedule.update_status()

    # Retry payment using backup funding source if it is available
    if schedule.can_retry_with_backup_funding_source():
        logger.info("Retrying payment (id=%s, status=%s) using backup funding source(id=%s, was=%s)" % (
            payment_id, payment_status, schedule.backup_funding_source_id, funding_source_id
        ), extra={
            'payment_id': payment_id,
            'schedule_id': schedule_id,
            'schedule.backup_funding_source_id': schedule.backup_funding_source_id
        })

        make_payment.delay(
            user_id=str(schedule.origin_user_id),
            payment_account_id=str(schedule.origin_payment_account_id),
            schedule_id=str(schedule.id),
            currency=str(schedule.currency.value),
            payment_amount=amount,  # NOTE: use the same amount of original payment!
            additional_information=str(schedule.additional_information),
            payee_id=str(schedule.payee_id),
            funding_source_id=str(schedule.backup_funding_source_id),  # NOTE: This time, use backup funding source!
            parent_payment_id=payment_id,  # NOTE: specify originating payment, to be able to track payment chains
            request_id=request_id
        )
        return


# Must NOT be executed in transaction. This requirement comes from "make_payment" requirements.
@shared_task
def make_overdue_payment(schedule_id: str, request_id=None):
    """
    Tries to make follow-up payments based on last failed list of payments for specific schedule.
    :param schedule_id:
    :param request_id: Unique processing request's id
    :return:
    """
    request_id = request_id if request_id else RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info("Processing overdue payment from schedule (id=%s)" % schedule_id, extra={
        'schedule_id': schedule_id
    })

    try:
        schedule = Schedule.objects.get(id=schedule_id)  # type: Schedule
    except Exception:
        logger.error("Unable to fetch schedule (id=%s) from DB: %r" % (schedule_id, format_exc()), extra={
            'schedule_id': schedule_id
        })
        return

    if schedule.processing:
        logger.error("Schedule (id=%s) is in processing state, skipping overdue payments" % schedule_id, extra={
            'schedule_id': schedule_id
        })
        return

    # block from multiple overdue events
    # (for example, accidentally clicking multiple times a 'pay overdue' button)
    schedule.processing = True

    # Select all SchedulePayments which are last in chains and are not in SUCCESS status
    overdue_payments = LastSchedulePayments.objects.filter(
        schedule_id=schedule_id,
        payment_status__in=[PaymentStatusType.FAILED, PaymentStatusType.REFUND, PaymentStatusType.CANCELED]
    ).order_by("created_at")  # type: list[LastSchedulePayments]

    logger.info("Total overdue payments (schedule_id=%s): %s" % (schedule_id, len(overdue_payments)), extra={
        'schedule_id': schedule_id
    })

    for op in overdue_payments:
        logger.info("Making new payment from overdue (id=%s, payment_id=%s, parent_payment_id=%s)" % (
            op.id, op.payment_id, op.parent_payment_id
        ), extra={
            'schedule_payment_id': op.id,
            'schedule_id': schedule_id,
            'payment_id': op.payment_id,
            'parent_payment_id': op.parent_payment_id
        })
        # INFO: this is synchronous code involving a series of HTTP requests to Payment API
        payment = make_payment(
            user_id=str(schedule.origin_user_id),
            payment_account_id=str(schedule.origin_payment_account_id),
            schedule_id=str(schedule_id),
            currency=str(schedule.currency.value),
            payment_amount=int(op.original_amount),  # NOTE: use original amount saved at the time of initial payment!
            additional_information=str(schedule.additional_information),
            payee_id=str(schedule.payee_id),
            funding_source_id=str(schedule.funding_source_id),  # NOTE: always retry using primary FS
            parent_payment_id=str(op.payment_id),  # NOTE: keep payment chain in order!
            request_id=request_id
        )
        logger.info("Created payment from overdue (id=%s, payment_id=%s, parent_payment_id=%s) result : %r" % (
            op.id, op.payment_id, op.parent_payment_id, payment), extra={
            'schedule_id': schedule_id,
            'payment_id': payment.id if payment is not None else None
        })

        # If we faced with some problems during payment's creation we stop sending overdue payments
        if payment is None or payment.status is PaymentStatusType.FAILED:
            logger.error("Payment failed from overdue (id=%s, payment_id=%s, parent_payment_id=%s). stop " % (
                op.id, op.payment_id, op.parent_payment_id), extra={
                'schedule_payment_id': op.id,
                'schedule_id': schedule_id,
                'payment_id': op.payment_id
            })
            break

    # Processing is over and we can allow user to use "Pay overdue" again if he wants
    schedule.processing = False


def process_all_deposit_payments(scheduled_date):
    """
    Process all deposit payments for specified date
    :param scheduled_date:
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all deposit payments for date: {scheduled_date}", extra={
        # TODO: how are datetime types handled in logging.extra ??
        'scheduled_date': scheduled_date
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = DepositsSchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES
    ).order_by("created_at")
    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):
            s = s  # type: DepositsSchedule
            logger.info("Submit deposit payment (schedule_id=%s, origin_user_id=%s, "
                        "origin_payment_account_id=%s, deposit_payment_amount=%s, period=%s)" % (
                            s.id, s.origin_user_id, s.origin_payment_account_id, s.deposit_amount, s.period
                        ),
                        extra={
                            'schedule_id': s.id,
                            'funding_source_id': s.funding_source_id,
                            'amount': s.deposit_amount,
                            'period': s.period
                        })

            # submit task for asynchronous processing to queue
            make_payment.delay(
                user_id=str(s.origin_user_id),
                payment_account_id=str(s.origin_payment_account_id),
                schedule_id=str(s.id),
                currency=str(s.currency.value),
                payment_amount=int(s.deposit_amount),
                additional_information=str(s.deposit_additional_information),
                payee_id=str(s.payee_id),
                funding_source_id=str(s.funding_source_id),
                request_id=request_id,
                is_deposit=True
            )

    logger.info(f"Finished deposit payments ({scheduled_date}) processing.", extra={'logGlobalDuration': True})


def submit_scheduled_payment(s: Schedule, request_id=None):
    """
    A common method to submit payments for execution
    :param s:
    :param request_id: Unique processing request's id
    :return:
    """
    logger.debug("Submit regular payment (schedule_id=%s, origin_user_id=%s, payment_account_id=%s, "
                 "origin_payment_amount=%s, deposit_payment_amount=%s, period=%s)" % (
                     s.id, s.origin_user_id, s.origin_payment_account_id, s.payment_amount, s.deposit_amount, s.period
                 ),
                 extra={
                     'schedule_id': s.id,
                     'funding_source_id': s.funding_source_id,
                     'amount': s.payment_amount,
                     'period': s.period
                 })

    # submit task for asynchronous processing to queue
    make_payment.delay(
        user_id=str(s.origin_user_id),
        payment_account_id=str(s.origin_payment_account_id),
        schedule_id=str(s.id),
        currency=str(s.currency.value),
        payment_amount=int(s.payment_amount),
        additional_information=str(s.additional_information),
        payee_id=str(s.payee_id),
        funding_source_id=str(s.funding_source_id),
        request_id=request_id
    )


def process_all_one_time_payments(scheduled_date):
    """
    Process all one-time payments for specified date
    :param scheduled_date:
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all one time payments for date: {scheduled_date}", extra={
        'scheduled_date': scheduled_date
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = OnetimeSchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES
    ).order_by("created_at")
    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s, request_id)

    logger.info(f"Finished one time payments ({scheduled_date}) processing.", extra={'logGlobalDuration': True})


def process_all_weekly_payments(scheduled_date):
    """
    Process all weekly payments for specified date
    :param scheduled_date:
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all weekly payments for date: {scheduled_date}", extra={
        'scheduled_date': scheduled_date
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = WeeklySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES
    ).order_by("created_at")
    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s, request_id)

    logger.info(f"Finished weekly payments ({scheduled_date}) processing.", extra={'logGlobalDuration': True})


def process_all_monthly_payments(scheduled_date):
    """
    Process all monthly payments for specified date
    :param scheduled_date:
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all monthly payments for date: {scheduled_date}", extra={
        'scheduled_date': scheduled_date
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = MonthlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES
    ).order_by("created_at")
    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s, request_id)

    logger.info(f"Finished monthly payments ({scheduled_date}) processing.", extra={'logGlobalDuration': True})


def process_all_quarterly_payments(scheduled_date):
    """
    Process all quarterly payments for specified date
    :param scheduled_date:
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all quarterly payments for date: {scheduled_date}", extra={
        'scheduled_date': scheduled_date
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = QuarterlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES
    ).order_by("created_at")
    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s, request_id)

    logger.info(f"Finished quarterly payments ({scheduled_date}) processing.", extra={'logGlobalDuration': True})


def process_all_yearly_payments(scheduled_date):
    """
    Process all yearly payments for specified date
    :param scheduled_date:
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all yearly payments for date: {scheduled_date}", extra={
        'scheduled_date': scheduled_date
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = YearlySchedule.objects.filter(
        scheduled_date=scheduled_date,
        status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES
    ).order_by("created_at")
    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):
            submit_scheduled_payment(s, request_id)

    logger.info(f"Finished yearly payments ({scheduled_date}) processing.", extra={'logGlobalDuration': True})


@shared_task
def initiate_daily_payments():
    """
    Initial entry point task which iterates through all Schedules and initiates payment tasks if dates match.

    :return:
    """
    logging.init_shared_extra()

    # get current date
    now = arrow.utcnow()

    logger.info(f"Starting daily ({now}) payments processing...", extra={
        'BLACKLISTED_DAYS_MAX_RETRY_COUNT': BLACKLISTED_DAYS_MAX_RETRY_COUNT
    })

    if BlacklistDate.contains(now.datetime.date()):
        logger.info("Skipping scheduler execution because '%s' is a special day" % now)
        return

    retry_count = 1
    scheduled_date = now

    while True:
        if retry_count > BLACKLISTED_DAYS_MAX_RETRY_COUNT:
            logger.info("Reached maximum BLACKLISTED_DAYS_MAX_RETRY_COUNT=%s. Stopping dates verification "
                        "and payment processing." % BLACKLISTED_DAYS_MAX_RETRY_COUNT)
            break

        # During first iteration we will process schedules for today
        process_all_payments_for_date(scheduled_date.datetime)

        # Taking next day as scheduled date that should be verified and processed if necessary
        scheduled_date = scheduled_date.shift(days=1)
        logger.info(f"Finished with processing all payments, check if next date ({scheduled_date}) "
                    f"is blacklisted (retry_count={retry_count})")
        # Check if specified date is not blacklisted, i.e. NOT weekend and/or special day
        if not BlacklistDate.contains(scheduled_date.date()):
            # No need to continue because scheduler will be executed on "scheduled_date"
            # and will process all schedules in "normal" way
            break

        retry_count += 1

    logger.info(f"Finished daily ({now}) payments processing.", extra={'logGlobalDuration': True})


def process_all_payments_for_date(date):
    """

    :param date:
    :rtype date: datetime.datetime
    :return:
    """
    logger.info(f"Process all payments for date: {date}")
    # process deposit payments first
    process_all_deposit_payments(date)
    process_all_one_time_payments(date)
    process_all_weekly_payments(date)
    process_all_monthly_payments(date)
    process_all_quarterly_payments(date)
    process_all_yearly_payments(date)


@shared_task
def on_payee_change(payee_info: Dict):
    """
    Process notification about changes in Payee model received from Payment-api.
    :param payee_info:
    :return:
    """
    pass
    # TODO: update all payee info that is stored in Django models
