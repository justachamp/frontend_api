# -*- coding: utf-8 -*-

from typing import Dict
from traceback import format_exc
import logging
import arrow

from django.conf import settings

from core.fields import Currency, TransactionStatusType
from frontend_api.models import Schedule
from frontend_api.models import UserAccount
from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from frontend_api.notifications.helpers import (
    prettify_number,
    send_bulk_emails,
    send_bulk_smses,
    get_funds_senders,
    get_funds_recipients,
    get_ses_email_payload
)
from core.models import User

logger = logging.getLogger(__name__)

# Need to get transaction type for passing transaction_type to templates
# Key is a transaction name from payment service, value is transaction type for appearance in templates
transaction_names = {
    "CreditCardToWallet": "Card",
    "DirectDebitToWallet": "Direct Debit",
    "WalletToIban": "External",
    "IncomingInternal": "Internal",
    "OutgoingInternal": "Internal",
    "IbanToWallet": "Bank Transfer"
}


def get_load_funds_details(transaction_info: Dict) -> Dict:
    now = arrow.utcnow()
    context = {
        "transaction_type": transaction_names.get(transaction_info.get("name"), "Unknown"),
        "error_message": transaction_info.get("error_message") or "unknown",
        'currency': Currency(transaction_info.get("currency")),
        'amount': transaction_info.get("amount"),
        'processed_datetime': now.datetime,
        'closing_balance': transaction_info.get("closing_balance"),
        # identifier explicitly specifies that funds has increased
        'sign': "+"
    }
    return context


def get_schedule_details(user: User, schedule: Schedule,
                         transaction_status: TransactionStatusType,
                         transaction_info: Dict) -> dict:
    """
    Retrieve context for templates with payment amount.
    :param transaction_info:
    :param transaction_status:
    :param user:
    :param schedule:
    :return:
    """
    now = arrow.utcnow()
    context = {
        'currency': schedule.currency,
        'amount': transaction_info.get("amount"),
        'processed_datetime': now.datetime,
        'schedule_name': schedule.name,
        'transaction_type': transaction_names.get(transaction_info.get("name"), "Unknown"),
        # identifier specifies either funds has increased or decreased
        'sign': "-" if int(transaction_info["amount"]) < 0 else '+'
    }
    return context


def invite_payer(schedule: Schedule) -> None:
    """
    Notify user if new 'receive' schedule was created and he is a payer.
    :param schedule:
    :return:
    """
    logger.info("Start invite payee. Schedule id: %s, status: %s, purpose: %s"
                % (schedule.id, schedule.status, schedule.purpose))
    payer = schedule.origin_user
    schedule_details = {
        "payer": payer.email,
        "payee": schedule.recipient_user.email,
        "link": "https://%s/" % settings.APP_WWW_HOST
    }
    payers = get_funds_senders(funds_sender=payer)
    emails = [user.email for user in payers if user.notify_by_email and user.email]
    logger.info("Invite payee. Send email notifications to: %s" % ", ".join(emails))
    send_bulk_emails(emails=emails,
                     context=schedule_details,
                     tpl_filename="notifications/email_invite_payer.html")


def notify_about_loaded_funds(user_id: str, transaction_info: Dict, transaction_status: TransactionStatusType) -> None:
    """
    Sends notification to user about updated balance after 'load funds' operation has completed.
    :param: user_id
    :param: transaction_info
    :param: transaction_status
    :return:
    """
    if transaction_status not in [TransactionStatusType.SUCCESS, TransactionStatusType.FAILED]:
        return
    try:
        funds_recipient = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.info("User with given user_id has not found. %r" % format_exc())
        return
    logger.info("Start notify about loaded funds. Transaction_info: %s" % transaction_info)

    message_tpl = {
        TransactionStatusType.SUCCESS:
            ",".join(
                ["Successful transaction: {sign}{amount}{cur_symbol}",
                 "\n{dt}",
                 "\n{transaction_type}",
                 "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."]
            ),
        TransactionStatusType.FAILED:
            ",".join(
                ["Failed transaction: {sign}{amount}{cur_symbol}",
                 "\n{dt}",
                 "\n{transaction_type}",
                 "\nReason: {error_msg}",
                 "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."]
            )
    }[transaction_status]

    tpl_filename = {
        TransactionStatusType.SUCCESS: 'notifications/email_recipients_balance_updated.html',
        TransactionStatusType.FAILED: 'notifications/email_transaction_failed.html'
    }[transaction_status]

    funds_recipients = get_funds_recipients(funds_recipient=funds_recipient)
    load_funds_details = get_load_funds_details(transaction_info)
    emails = [user.email for user in funds_recipients if user.notify_by_email and user.email]
    logger.info("Load funds. Funds recipient emails: %s" % ", ".join(emails))
    send_bulk_emails(emails=emails,
                     context=load_funds_details,
                     tpl_filename=tpl_filename)

    sms_context = {
        "transaction_type": load_funds_details.get("transaction_type"),
        "error_msg": load_funds_details.get("error_message") or "unknown",
        "amount": prettify_number(load_funds_details['amount']),
        "cur_symbol": load_funds_details["currency"].symbol,
        "dt": arrow.get(load_funds_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
        "closing_balance": prettify_number(load_funds_details["closing_balance"]),
        'sign': load_funds_details.get('sign')
    }
    phone_numbers = [user.phone_number for user in funds_recipients if user.notify_by_phone and user.phone_number]
    logger.info("Load funds. Funds recipient phone numbers: %s" % ", ".join(phone_numbers))
    send_bulk_smses(phone_numbers=phone_numbers,
                    context=sms_context,
                    tpl_message=message_tpl)


def notify_about_schedules_failed_payment(schedule: Schedule, transaction_info: Dict) -> None:
    """
    Sends notifications for funds sender if transaction has failed.
    :param transaction_info:
    :param schedule:
    :return:
    """
    logger.info("Start notify about failed payment. Transaction info: %s" % transaction_info)
    funds_sender = schedule.origin_user
    payment_account_id = transaction_info.get("account_id")

    try:
        payment_account = UserAccount.objects.get(payment_account_id=payment_account_id)
    except UserAccount.DoesNotExist:
        logger.error("UserAccount with given payment account id was not found. %r" % format_exc())
        return

    message_tpl = ",".join([
        "Failed transaction: {sign}{amount}{cur_symbol}",
        "\n{dt}",
        "\n{transaction_type}, {schedule_name}",
        "\nReason: {error_msg}",
        "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."
    ])

    if payment_account.id in funds_sender.get_all_related_account_ids():
        funds_senders = get_funds_senders(funds_sender=funds_sender)
        closing_balance = transaction_info.get("closing_balance")
        error_message = transaction_info.get("error_message") or 'unknown'
        schedule_details = get_schedule_details(
            user=funds_sender,
            schedule=schedule,
            transaction_status=TransactionStatusType.FAILED,
            transaction_info=transaction_info)
        email_context = {"closing_balance": closing_balance,
                         "error_message": error_message,
                         **schedule_details}
        emails = [user.email for user in funds_senders if user.notify_by_email and user.email]
        logger.info("Failed payment. Funds senders emails: %s ." % ", ".join(emails))
        send_bulk_emails(emails=emails,
                         context=email_context,
                         tpl_filename='notifications/email_transaction_failed.html')

        # Extract funds senders and send sms notifications about failed transaction
        sms_context = {
            "transaction_type": schedule_details.get("transaction_type"),
            "amount": prettify_number(schedule_details['amount']),
            "cur_symbol": schedule_details["currency"].symbol,
            "dt": arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
            "error_msg": error_message,
            "schedule_name": schedule.name if len(schedule.name) < 20 else schedule.name[:20] + '...',
            "closing_balance": prettify_number(closing_balance),
            "sign": schedule_details.get("sign")
        }
        phone_numbers = [user.phone_number for user in funds_senders if user.notify_by_phone and user.phone_number]
        logger.info("Failed payment. Funds senders phone numbers: %s ." % ", ".join(phone_numbers))
        send_bulk_smses(phone_numbers=phone_numbers,
                        context=sms_context,
                        tpl_message=message_tpl)
    else:
        logger.info("Notifications sending has passed. Schedule id: %s" % schedule.id)


def notify_about_schedules_successful_payment(schedule: Schedule, transaction_info: Dict) -> None:
    """
    Send notifications for funds senders and recipients in case of successful transaction.
    :param schedule:
    :param transaction_info: data from payment service.
    :return:
    """
    logger.info("Start notify about successful payment. Transaction info: %s" % transaction_info)
    funds_sender = schedule.origin_user  # type: User
    funds_recipient = schedule.recipient_user if schedule.recipient_user \
        else schedule.payee_recipient_email
    payment_account_id = transaction_info.get("account_id")
    try:
        payment_account = UserAccount.objects.get(payment_account_id=payment_account_id)
    except UserAccount.DoesNotExist:
        logger.error("UserAccount with given payment account id was not found. %r" % format_exc())
        return

    outgoing_payment_message_tpl = ",".join([
        "Successful transaction: {sign}{amount}{cur_symbol}",
        "\n{dt}",
        "\n{transaction_type}, {schedule_name}",
        "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."
    ])

    # Send notifications for funds SENDERS.
    if payment_account.id in funds_sender.get_all_related_account_ids():
        funds_senders = get_funds_senders(funds_sender=funds_sender)
        closing_balance = transaction_info.get("closing_balance")
        schedule_details = get_schedule_details(
            user=funds_sender,
            schedule=schedule,
            transaction_status=TransactionStatusType.SUCCESS,
            transaction_info=transaction_info)
        email_context_for_senders = {"closing_balance": closing_balance, **schedule_details}
        emails = [user.email for user in funds_senders if user.notify_by_email and user.email]
        logger.info("Successful payment. Funds senders emails: %s" % ", ".join(emails))
        send_bulk_emails(emails=emails,
                         context=email_context_for_senders,
                         tpl_filename='notifications/email_senders_balance_updated.html')
        sms_context = {
            "transaction_type": schedule_details.get("transaction_type"),
            "amount": prettify_number(schedule_details['amount']),
            "cur_symbol": schedule_details["currency"].symbol,
            "dt": arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
            "schedule_name": schedule.name if len(schedule.name) < 20 else schedule.name[:20] + '...',
            "closing_balance": prettify_number(closing_balance),
            "sign": schedule_details.get("sign")
        }
        phone_numbers = [user.phone_number for user in funds_senders if user.notify_by_phone and user.phone_number]
        logger.info("Successful payment. Funds senders phone_numbers: %s" % ", ".join(phone_numbers))
        send_bulk_smses(phone_numbers=phone_numbers,
                        context=sms_context,
                        tpl_message=outgoing_payment_message_tpl)

    # Send notification for funds RECIPIENTS.
    if isinstance(funds_recipient, str):
        logger.info("Successful payment. External recipient: %s" % funds_recipient)
        schedule_details = get_schedule_details(
            user=funds_recipient,
            schedule=schedule,
            transaction_status=TransactionStatusType.SUCCESS,
            transaction_info=transaction_info)
        # External user should not get transaction type
        schedule_details["transaction_type"] = None
        message = get_ses_email_payload(
            tpl_filename='notifications/email_recipients_balance_updated.html',
            tpl_context=schedule_details,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        # Send email
        send_notification_email.delay(to_address=funds_recipient, message=message)
        return

    incoming_payment_message_tpl = ",".join([
        "Successful transaction: {sign}{amount}{cur_symbol}",
        "\n{dt}",
        "\n{transaction_type}, {schedule_name}",
        "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}"
    ])

    if payment_account.id in funds_recipient.get_all_related_account_ids():
        funds_recipients = get_funds_recipients(funds_recipient=funds_recipient)
        schedule_details = get_schedule_details(
            user=funds_recipient,
            schedule=schedule,
            transaction_status=TransactionStatusType.SUCCESS,
            transaction_info=transaction_info)
        closing_balance = transaction_info.get("closing_balance")
        email_context_for_recipients = {'closing_balance': closing_balance, **schedule_details}
        emails = [user.email for user in funds_recipients if user.notify_by_email and user.email]
        logger.info("Successful payment. Funds recipient emails: %s" % ", ".join(emails))
        send_bulk_emails(emails=emails,
                         context=email_context_for_recipients,
                         tpl_filename='notifications/email_recipients_balance_updated.html')

        sms_context = {
            "transaction_type": schedule_details.get("transaction_type"),
            "amount": prettify_number(schedule_details['amount']),
            "cur_symbol": schedule_details["currency"].symbol,
            "dt": arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
            "schedule_name": schedule.name if len(schedule.name) < 20 else schedule.name[:20] + '...',
            "closing_balance": prettify_number(closing_balance),
            "sign": schedule_details.get("sign")
        }
        phone_numbers = [user.phone_number for user in funds_recipients if user.notify_by_phone and user.phone_number]
        logger.info("Successful payment. Funds recipient phone numbers: %s" % ", ".join(phone_numbers))
        send_bulk_smses(phone_numbers=phone_numbers,
                        context=sms_context,
                        tpl_message=incoming_payment_message_tpl)
        logger.info("Successful payment. Notifications sent to all participants. Schedule id: %s " % schedule.id)
    else:
        logger.info("Successful payment. Notifications sending has passed.")
