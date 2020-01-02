from __future__ import absolute_import, unicode_literals
from typing import Dict
from datetime import datetime
from traceback import format_exc
import logging
from uuid import UUID, uuid4, uuid5, NAMESPACE_OID

import arrow
from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import IntegrityError
from django.core.paginator import Paginator
from django.conf import settings
from django.db import transaction
from django.db.models import Q

from core.logger import RequestIdGenerator
from core.models import User
from core.fields import Currency, PaymentStatusType, TransactionStatusType, FundingSourceType

import external_apis.payment.service as payment_service

from frontend_api.models.blacklist import BlacklistDate, BLACKLISTED_DAYS_MAX_RETRY_COUNT
from frontend_api.models.schedule import Schedule, PeriodicSchedule, DepositsSchedule
from frontend_api.models.schedule import SchedulePayments, LastSchedulePayments
from frontend_api.models.escrow import Escrow, EscrowStatus
from frontend_api.fields import ScheduleStatus, SchedulePeriod
from frontend_api.notifications.schedules import (
    notify_about_loaded_funds,
    notify_about_schedules_successful_payment,
    notify_about_schedules_failed_payment
)
from frontend_api.notifications.escrows import (
    notify_about_fund_escrow_state,
    notify_parties_about_funds_transfer,
    notify_escrow_funder_about_transaction_status
)

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


# Must NOT be executed in transaction, in this way we guarantee that SchedulePayment will be created even if something
# goes wrong after that. SchedulePayment record will eventually prevent making extra requests to PaymentApi
# upon second run for the same payment.
@shared_task
def make_payment(user_id: str, payment_account_id: str, schedule_id: str, currency: str, payment_amount: int,
                 additional_information: str, payee_id: str, funding_source_id: str, parent_payment_id=None,
                 execution_date=None, request_id=None, is_deposit=False, original_scheduled_date=None):
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
    :param original_scheduled_date: Initially planned date of payment according to PeriodicSchedule
                                    w/o any date adjustments like weekends and/or blacklisted dates
    :return: created payment instance
    """
    logging.init_shared_extra(request_id)
    payment_id = uuid4()
    logger.info("Making payment: payment_id=%s, user_id=%s, payment_account_id=%s, schedule_id=%s, currency=%s, "
                "payment_amount=%s, additional_information=%s, payee_id=%s, funding_source_id=%s, parent_payment_id=%s,"
                " execution_date=%s, is_deposit=%s, original_scheduled_date=%s, request_id=%s" % (
                    payment_id, user_id, payment_account_id, schedule_id, currency, payment_amount,
                    additional_information, payee_id, funding_source_id, parent_payment_id,
                    execution_date, is_deposit, original_scheduled_date,
                    request_id
                ),
                extra={
                    'schedule_id': schedule_id,
                    'payment_id': payment_id,
                    'funding_source_id': funding_source_id,
                    'payment_amount': payment_amount,
                    'is_deposit': is_deposit,
                })

    result = None

    idempotence_key = {
        False: "%s.%s.%s.%s.%s.%s.%s.%s" % (
            user_id, payment_account_id, schedule_id, currency, payment_amount,
            payee_id, parent_payment_id,
            original_scheduled_date
        ),
        # make sure we only have SINGLE deposit payment within specific schedule
        True: "%s.%s.%s" % (
            schedule_id, payee_id, parent_payment_id,
        )
    }[is_deposit]

    try:
        schedule_payment = SchedulePayments(
            schedule_id=schedule_id,
            payment_id=payment_id,
            funding_source_id=funding_source_id,
            parent_payment_id=parent_payment_id,
            payment_status=PaymentStatusType.PENDING,
            original_amount=payment_amount,
            is_deposit=is_deposit,
            idempotence_key=uuid5(NAMESPACE_OID, idempotence_key)
        )
        schedule_payment.save()
        logger.info("Schedule payment successfully created (schedule_id=%s, payment_id=%s)" % (schedule_id, payment_id))

    except IntegrityError as e:
        if not ("duplicate" and "idempotence_key" in str(e)):
            raise e
        logger.error("Looks like double-charge payment attempt(idempotence_key=%s), exiting" % idempotence_key, extra={
            'schedule_id': schedule_id,
            'payment_id': payment_id,
            'funding_source_id': funding_source_id,
            'payment_amount': payment_amount,
            'is_deposit': is_deposit,
        })
        return result
    except Exception:
        logger.error("Saving schedule_payment record failed due to: %r" % format_exc(), extra={
            'schedule_id': schedule_id,
        })
        return result

    logger.info("Schedule payment record was created (id=%r)" % schedule_payment.id, extra={
        'schedule_payment_id': schedule_payment.id
    })

    try:

        result = payment_service.Payment.create(
            payment_id=payment_id,
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
        )

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


def process_schedule_transaction_change(transaction_info: Dict):
    """
    Handle Schedule related transaction changes
    :param transaction_info:
    :return:
    """
    transaction_id = transaction_info.get("transaction_id")
    schedule_id = transaction_info.get("schedule_id")
    transaction_status = TransactionStatusType(transaction_info.get("status"))
    is_hidden = bool(int(transaction_info.get("is_hidden", 0)))

    # Do not notify about hidden transactions
    if is_hidden:
        logger.info("Omit sending notification about transaction(id=%s), since it's hidden" % transaction_id)
        return

    try:
        schedule = Schedule.objects.get(id=schedule_id)
    except Schedule.DoesNotExist:
        logger.info("Schedule with id %s was not found. %r" % (schedule_id, format_exc()))
        return

    logger.info("Processing transaction_id=%s for schedule_id=%s" % (transaction_id, schedule_id))
    # Send notifications about completed schedules.
    if transaction_status is TransactionStatusType.SUCCESS:
        notify_about_schedules_successful_payment(schedule=schedule, transaction_info=transaction_info)
    elif transaction_status is TransactionStatusType.FAILED:
        notify_about_schedules_failed_payment(schedule=schedule, transaction_info=transaction_info)


def process_escrow_transaction_change(transaction_info: Dict):
    """
    Handle Escrow-related transaction changes
    :param transaction_info:
    :return:
    """
    transaction_id = transaction_info.get("transaction_id")
    transaction_status = TransactionStatusType(transaction_info.get("status"))
    wallet_id = transaction_info.get("wallet_id")
    wallet_id = UUID(wallet_id) if wallet_id else None
    escrow_id = transaction_info.get("escrow_id")
    payee_id = transaction_info.get("payee_id")  # recipient of money
    payee_id = UUID(payee_id) if payee_id else None
    funding_source_id = transaction_info.get("funding_source_id")  # origin of money
    funding_source_id = UUID(funding_source_id) if funding_source_id else None
    funding_source_type = transaction_info.get("funding_source_type")
    funding_source_type = FundingSourceType(funding_source_type) if funding_source_type else None
    closing_balance = transaction_info.get("closing_balance")
    is_hidden = bool(int(transaction_info.get("is_hidden", 0)))

    # Do not process transactions that are still processing
    if transaction_status in Escrow.PENDING_TRANSACTION_STATUSES:
        logger.info("Skipping escrow transaction(id=%s) handling, since status=%r" % (
            transaction_id, transaction_status
        ))
        return

    # figure out Escrow for processing
    escrow = find_escrow_by_criteria(payment_info=transaction_info)  # type: Escrow

    if escrow is None:
        logger.info("Unable to find matching Escrow, which corresponds to transaction_info=%r" % transaction_info)
        return

    # There are some risks if we will cast to int during first variable declaration: incoming value could be "null" (for
    # pending/processing transactions) and we will get ValueError
    closing_balance = int(closing_balance)
    # Pending/processing transaction doesn't have value in closing balance field, so we should update Escrow's balance
    # only after verification for transaction's status.
    escrow.update_balance(closing_balance)

    # Do not notify about hidden transactions
    if is_hidden:
        logger.info("Omit sending notification about transaction(id=%s), since it's hidden" % transaction_id)
        return

    try:
        # Since escrow is 2-stage process, i.e.  Funder -> Escrow Wallet -> Recipient,
        # we need to figure out which stage we're currently on (F->E, or E->R), to do this we'll use
        # `payee_id` and `funding_source_id`

        # F->E Stage: money gets into Escrow wallet
        if payee_id == escrow.transit_payee_id:
            logger.info("Notify parties about transaction status and balance amount after Escrow funding attempts.\
                        Transaction info: %s" % transaction_info)
            if transaction_status in [TransactionStatusType.SUCCESS]:
                # Send notification to recipient
                notify_about_fund_escrow_state(
                    escrow=escrow,
                    transaction_info=transaction_info
                )

            # There is a special case/scenario when we are trying to Load funds to an Escrow from WALLET, this kind of
            # payment (WalletToVirtualWallet) has two created payments in case in failure, and we will receive two
            # notifications, to avoid duplicates with notifications we need to ignore one of them. To do so, we added
            # verification by funding source's type (so notification will be created by "process_general_money_movement")
            if transaction_status in [TransactionStatusType.FAILED] and funding_source_type is not FundingSourceType.WALLET:
                notify_escrow_funder_about_transaction_status(
                    escrow=escrow,
                    transaction_info=transaction_info,
                    tpl_filename='notifications/email_transaction_failed.html',
                )

        # E->R Stage: money leaves Escrow wallet ()
        if funding_source_id == escrow.transit_funding_source_id:
            # "Release" it's not common name for "OutgoingInternal" transaction, so we pre-set it like this
            # Footer replaces "(Wallet=>Escrow) available balance:" in template.
            additional_context = {'transaction_type': 'Release', "footer": "Escrow available balance"}

            # Send notification for SUCCESS transaction only if this transaction is related to "Release" operation
            # (payee in this case will belong to Recipient) it could be that it's a "Close" operation as well (payee
            # will belong to Funder), but we don't need to inform funder with this notification in this case
            # (he will be informed by "IncomingInternal" payment)
            if transaction_status in [TransactionStatusType.SUCCESS] and payee_id == escrow.payee_id:
                # Recipient will receive separate event for his own incoming payment, so we shouldn't worry about him
                # right here, just send notification to funder
                notify_escrow_funder_about_transaction_status(
                    escrow=escrow,
                    transaction_info=transaction_info,
                    tpl_filename='notifications/email_users_balance_updated.html',
                    additional_context=additional_context
                )

            if transaction_status in [TransactionStatusType.FAILED]:
                notify_escrow_funder_about_transaction_status(
                    escrow=escrow,
                    transaction_info=transaction_info,
                    tpl_filename="notifications/email_transaction_failed.html",
                    additional_context=additional_context
                )

    except Exception:
        logger.error("Unable to process notifications for Escrow id=%s, exc=%r" % (escrow_id, format_exc()))


def process_general_money_movement(transaction_info: Dict):
    """
    Any logic not related to processing specific Escrow and/or Schedule
    :param transaction_info:
    :return:
    """
    transaction_id = transaction_info.get("transaction_id")
    user_id = transaction_info.get("user_id")
    transaction_name = transaction_info.get("name")
    transaction_status = TransactionStatusType(transaction_info.get("status"))
    is_hidden = bool(int(transaction_info.get("is_hidden", 0)))

    # Do not notify about hidden transactions
    if is_hidden:
        logger.info("Omit sending notification about transaction(id=%s), since it's hidden" % transaction_id)
        return

    # Send notifications about loaded funds
    notify_about_loaded_funds(
        user_id=user_id,
        transaction_info=transaction_info,
        transaction_status=transaction_status,
        additional_context=get_general_money_movement_additional_context(transaction_info)
    )


def get_general_money_movement_additional_context(transaction_info: Dict) -> Dict:
    # It's common notification, but we would like to add Escrow's name to it (because notification template has it),
    # if transaction contains link to any
    result = {}
    escrow = get_transaction_related_escrow(transaction_info)
    if escrow is not None:
        result.update({'name': escrow.name})

    return result


@shared_task
@transaction.atomic
def on_transaction_change(transaction_info: Dict):
    """
    Process events from payments service.
    :param transaction_info:
    :return:
    """
    logger.info("Start on_transaction_change. Transaction info: %s." % transaction_info)
    transaction_id = transaction_info.get("transaction_id")
    transaction_status = TransactionStatusType(transaction_info.get("status"))
    user_id = transaction_info.get("user_id")
    schedule_id = transaction_info.get("schedule_id")
    payee_id = transaction_info.get("payee_id")  # recipient of money
    funding_source_id = transaction_info.get("funding_source_id")  # origin of money
    wallet_id = transaction_info.get("wallet_id")
    escrow_id = transaction_info.get("escrow_id")
    request_id = RequestIdGenerator.get()

    logging.init_shared_extra(request_id)
    logger.info("Received 'transaction changed' event, starting processing (transaction_id=%s, transaction_info=%r)" % (
        transaction_id, transaction_info
    ), extra={
        'request_id': request_id,
        'user_id': user_id,
        'transaction_id': transaction_id,
        'schedule_id': schedule_id,
        'escrow_id': escrow_id,
        'wallet_id': wallet_id,
        'funding_source_id': funding_source_id,
        'payee_id': payee_id,
        'transaction_status': transaction_status,
    })

    if is_schedule_related_transaction(transaction_info):
        process_schedule_transaction_change(transaction_info=transaction_info)
    elif is_escrow_wallet_related_transaction(transaction_info):
        process_escrow_transaction_change(transaction_info=transaction_info)
    else:
        process_general_money_movement(transaction_info=transaction_info)


def is_schedule_related_transaction(transaction_info: Dict):
    transaction_id = transaction_info.get("transaction_id")
    schedule_id = transaction_info.get("schedule_id")

    result = schedule_id is not None and Schedule.objects.filter(id=schedule_id).exists()
    logger.info("is_schedule_related_transaction returned %s for transaction_id=%s" % (result, transaction_id), extra={
            'transaction_id': transaction_id,
            'schedule_id': schedule_id
        })
    return result


def is_escrow_wallet_related_transaction(transaction_info: Dict):
    transaction_id = transaction_info.get("transaction_id")
    wallet_id = transaction_info.get("wallet_id")

    result = Escrow.objects.filter(wallet_id=wallet_id).exists()
    logger.info("is_escrow_wallet_related_transaction returned %s for transaction_id=%s" % (
        result, transaction_id
    ), extra={
        'transaction_id': transaction_id,
        'wallet_id': wallet_id
    })
    return result


def get_transaction_related_escrow(transaction_info: Dict):
    transaction_id = transaction_info.get("transaction_id")
    escrow_id = transaction_info.get("escrow_id")
    result = None

    try:
        result = Escrow.objects.get(id=escrow_id)
    except ObjectDoesNotExist:
        logger.debug("Transaction (id=%s) does not contain reference to Escrow" % transaction_id)

    return result


def find_escrow_by_criteria(payment_info: Dict) -> Escrow or None:
    """
    Figure out which Escrow to use given input parameters
    :param payment_info:
    :return:
    """
    payment_id = payment_info.get("payment_id")
    escrow_id = payment_info.get("escrow_id")
    payee_id = payment_info.get("payee_id")
    funding_source_id = payment_info.get("funding_source_id")
    wallet_id = payment_info.get("wallet_id")

    # NOTE: Try to find matching Escrow using different criteria,
    # since we don't always get 'escrow_id' from payment-api
    escrow = None

    # CASE 0: try to find it by 'wallet_id' (looks like it should be present in all escrow-related payments)
    try:
        escrow = Escrow.objects.get(wallet_id=wallet_id)
        logger.info("payment_id=%s is related to Escrow(id=%s, status=%s) by wallet_id" % (
            payment_id, escrow.id, escrow.status
        ), extra={
            'payment_id': payment_id,
            'escrow_id': escrow.id,
            'escrow_status': escrow.status,
        })
    except ObjectDoesNotExist:
        logger.info("Unable to find Escrow by wallet_id=%s" % wallet_id)

    # # CASE 1: try to find it by 'escrow_id'
    # try:
    #     escrow = Escrow.objects.get(id=escrow_id)
    #     logger.info("payment_id=%s is related to Escrow(id=%s, status=%s) by escrow_id" % (
    #         payment_id, escrow.id, escrow.status
    #     ), extra={
    #         'payment_id': payment_id,
    #         'escrow_id': escrow.id,
    #         'escrow_status': escrow.status,
    #     })
    # except ObjectDoesNotExist:
    #     logger.info("Unable to find Escrow by  escrow_id=%s" % escrow_id)
    #
    # # CASE 2: try to find it by 'payee_id'
    # # In this case 'payee_id' == 'escrow.transit_payee_id', and this means that money goes from Funder -> Escrow
    # if escrow is None:
    #     try:
    #         escrow = Escrow.objects.get(transit_payee_id=payee_id)
    #         logger.info("payment_id=%s is related to Escrow(id=%s, status=%s) by payee_id" % (
    #             payment_id, escrow.id, escrow.status
    #         ), extra={
    #             'payment_id': payment_id,
    #             'escrow_id': escrow.id,
    #             'escrow_status': escrow.status,
    #         })
    #     except ObjectDoesNotExist:
    #         logger.info("Unable to find Escrow by payee_id=%s" % payee_id)
    #
    # # CASE 3: try to find it by 'funding_source_id'
    # # In this case, 'funding_source_id' == 'escrow.transit_funding_source_id'
    # if escrow is None:
    #     try:
    #         escrow = Escrow.objects.get(transit_funding_source_id=funding_source_id)
    #         logger.info("payment_id=%s is related to Escrow(id=%s, status=%s) by funding_source_id" % (
    #             payment_id, escrow.id, escrow.status
    #         ), extra={
    #             'payment_id': payment_id,
    #             'escrow_id': escrow.id,
    #             'escrow_status': escrow.status,
    #         })
    #     except ObjectDoesNotExist:
    #         logger.info("Unable to find Escrow by funding_source_id=%s" % funding_source_id)

    return escrow


def process_escrow_payment_change(payment_info: Dict):
    """
    Special code for handling Escrow-related payment events
    :param payment_info:
    :return:
    """
    payment_id = payment_info.get("payment_id")
    payment_status = PaymentStatusType(payment_info.get('status'))

    p_statuses = [PaymentStatusType.PENDING, TransactionStatusType.PROCESSING]
    if payment_status in p_statuses:
        logger.info("Skipping Escrow processing(payment_info=%r), since payment status is in %r" % (
            payment_info, p_statuses
        ))
        return

    # figure out Escrow for processing
    escrow = find_escrow_by_criteria(payment_info)  # type: Escrow

    if escrow is None:
        logger.info("Unable to find matching Escrow, which corresponds to payment_info=%r" % payment_info)
        return

    logger.info("Processing Escrow=%r" % escrow)

    # Note that balance is stored in transactions (not payment) and Escrow's balance will be updated during processing
    # 'on_transaction_changed' event

    # persist actual payment_info in our local Django model
    escrow.update_payment_info(
        status=PaymentStatusType(payment_info.get('status'))
    )

    # actually process Escrow
    try:
        if escrow.status is not EscrowStatus.pending_funding:
            logger.info("Skipping Escrow processing since status is not [%r], payment_id=%s" % (
                EscrowStatus.pending_funding, payment_id
            ))
            return

        if payment_status in [PaymentStatusType.FAILED, PaymentStatusType.REFUND, PaymentStatusType.CANCELED]:
            # We need to provide a way to repeat LoadFunds attempt, but creating new
            # LoadFundsEscrowOperation object could break our logic/idea that Escrow with "pending_funding"
            # status has only one LoadFunds operation, so we resetting "approve" flag's state
            escrow.last_load_funds_operation.reset_approved_state()
        else:
            logger.info("Moving escrow (id=%s) to %r state" % (escrow.id, EscrowStatus.ongoing), extra={
                'escrow_id': escrow.id
            })
            escrow.move_to_status(status=EscrowStatus.ongoing)

    except Exception:
        logger.error("Unable to process Escrow %r" % format_exc())


def process_schedule_payment_change(payment_info: Dict, request_id=None):
    """
    Process payment events in the context of Schedules
    :param payment_info:
    :return:
    """
    payment_id = payment_info.get("payment_id")
    payment_account_id = payment_info.get("account_id")
    schedule_id = payment_info.get("schedule_id")
    funding_source_id = payment_info.get("funding_source_id")
    payment_status = PaymentStatusType(payment_info.get('status'))
    amount = int(payment_info.get("amount"))

    if schedule_id is None:
        logger.info("Skipping payment (id=%s), it is not related to any schedule" % payment_id, extra={
            'request_id': request_id,
            'payment_id': payment_id
        })
        return

    try:
        schedule = Schedule.objects.get(id=schedule_id)  # type: Schedule
    except ObjectDoesNotExist:
        logger.error("Given schedule (id=%s) not found, exiting" % schedule_id, extra={
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
    if not schedule.can_retry_with_backup_funding_source():
        return

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


@shared_task
@transaction.atomic
def on_payment_change(payment_info: Dict):
    """
    Process notification about changes in Payment model received from Payment-api.
    :param payment_info:
    :return:
    """
    user_id = payment_info.get("user_id")
    payment_id = payment_info.get("payment_id")
    schedule_id = payment_info.get("schedule_id")
    escrow_id = payment_info.get("escrow_id")
    funding_source_id = payment_info.get("funding_source_id")
    payment_status = PaymentStatusType(payment_info.get('status'))
    request_id = payment_info.get("request_id", RequestIdGenerator.get())

    logging.init_shared_extra(request_id)
    logger.info("Received 'payment changed' event, starting processing (payment_id=%s, payment_info=%r)" % (
        payment_id, payment_info
    ), extra={
        'request_id': request_id,
        'user_id': user_id,
        'payment_id': payment_id,
        'schedule_id': schedule_id,
        'escrow_id': escrow_id,
        'funding_source_id': funding_source_id,
        'payment_status': payment_status,
    })

    # try to process payment event in the context of Escrow
    process_escrow_payment_change(payment_info=payment_info)

    # try to process payment event in the context of Schedule
    process_schedule_payment_change(payment_info=payment_info, request_id=request_id)


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

    # Select all SchedulePayment which are last in chains and are not in SUCCESS status
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


def process_all_deposit_payments(scheduled_date, is_execution_date_limited=True):
    """
    Process all deposit payments for specified date
    :param scheduled_date:
    :param is_execution_date_limited: bool
    :return:
    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all deposit payments for date: {scheduled_date}", extra={
        # TODO: how are datetime types handled in logging.extra ??
        'scheduled_date': scheduled_date,
        'is_execution_date_limited': is_execution_date_limited
    })

    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = DepositsSchedule.objects.filter(
        Q(scheduled_date=scheduled_date) &
        Q(status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES) &
        Schedule.is_execution_date_limited_filters(is_execution_date_limited)
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


def process_all_periodic_payments(scheduled_date: datetime, period: SchedulePeriod, is_execution_date_limited=True):
    """
    Process all Periodic (weekly, monthly, quarterly, yearly) payments for specified date
    :param scheduled_date:
    :type scheduled_date: datetime
    :param period:
    :type period: SchedulePeriod
    :param is_execution_date_limited: whether or not process payments with special restrictions to exection_date
    :return:

    """
    request_id = RequestIdGenerator.get()
    logging.init_shared_extra(request_id)
    logger.info(f"Process all periodic({period}) payments for date: {scheduled_date}", extra={
        'scheduled_date': scheduled_date,
        'period': str(period),
        'is_execution_date_limited': is_execution_date_limited
    })

    cls = Schedule.get_periodic_class(period)  # type: PeriodicSchedule
    # make sure we always keep consistent order, otherwise we'll get unpredictable results
    payments = cls.objects.filter(
        Q(scheduled_date=scheduled_date) &
        Q(status__in=Schedule.PROCESSABLE_SCHEDULE_STATUSES) &
        Schedule.is_execution_date_limited_filters(is_execution_date_limited)
    ).order_by("created_at")

    paginator = Paginator(payments, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for p in paginator.page_range:
        for s in paginator.page(p):  # type: PeriodicSchedule
            logger.debug("Submit regular payment (schedule_id=%s, origin_user_id=%s, payment_account_id=%s, "
                         "origin_payment_amount=%s, deposit_payment_amount=%s, period=%s)" % (
                             s.id, s.origin_user_id, s.origin_payment_account_id, s.payment_amount, s.deposit_amount,
                             s.period
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
                original_scheduled_date=s.original_scheduled_date,
                request_id=request_id
            )

    logger.info(f"Finished periodic({period}) payments ({scheduled_date}) processing.", extra={
        'logGlobalDuration': True
    })


def process_all_payments_for_date(date: datetime, is_execution_date_limited: bool):
    """
    Process all payments for specific date taking into account inforamtion about execution time.

    :param date:
    :param is_execution_date_limited:
    :rtype date: datetime.datetime
    :return:
    """
    logger.info("Process all payments for date=%s, is_execution_date_limited=%s" % (
        date, is_execution_date_limited
    ))
    # process deposit payments first
    process_all_deposit_payments(date, is_execution_date_limited)

    # process periodic payments
    for period in SchedulePeriod:
        process_all_periodic_payments(
            scheduled_date=date,
            period=period,
            is_execution_date_limited=is_execution_date_limited
        )


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

    retry_count = 1
    scheduled_date = now

    # We can safely start processing for payments that don't have any execution date limitation (in general, this is
    # about interaction with the bank): operations will be executed inside payment service and weekends & holidays
    # restrictions have no effect
    process_all_payments_for_date(scheduled_date.datetime, is_execution_date_limited=False)

    if BlacklistDate.contains(scheduled_date.datetime.date()):
        logger.info("Skipping scheduler execution because '%s' is a special day" % now)
        return

    while True:
        if retry_count > BLACKLISTED_DAYS_MAX_RETRY_COUNT:
            logger.info("Reached maximum BLACKLISTED_DAYS_MAX_RETRY_COUNT=%s. Stopping dates verification "
                        "and payment processing." % BLACKLISTED_DAYS_MAX_RETRY_COUNT)
            break

        # We already process payments that do not have any execution date limitation, now we will concentrate on
        # payments for which blacklisted dates are important. During first iteration we will process schedules for today
        process_all_payments_for_date(scheduled_date.datetime, is_execution_date_limited=True)

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


@shared_task
def on_payee_change(payee_info: Dict):
    """
    Process notification about changes in Payee model received from Payment-api.
    :param payee_info:
    :return:
    """
    logger.info("Received on_payee_change event, info=%r" % payee_info)
    # TODO: update all payee info that is stored in Django models
