# -*- coding: utf-8 -*-
from typing import Dict
from traceback import format_exc
import logging
import arrow
from copy import deepcopy
from django.template.loader import render_to_string
from django import template
from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q

from core.fields import Currency, TransactionStatusType, UserStatus
from frontend_api.models.schedule import Schedule
from frontend_api.models import UserAccount
from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms

logger = logging.getLogger(__name__)

User = get_user_model()

register = template.Library()


# Need to get transaction type for passing transaction_type to templates
# Key is a transaction name from payment service, value is transaction type for appearance in templates
transaction_names = {
    "CreditCardToCustomate": "Card",
    "DirectDebitToCustomate": "Direct Debit",
    "CustomateToIban": "External",
    "IncomingInternal": "Internal",
    "OutgoingInternal": "Internal",
    "IbanToCustomate": "Bank Transfer"
}


@register.filter
def prettify_number(value) -> str:
    """
    Prettifies balance number
    :param value:
    :return:
    """
    try:
        return "%0.2f" % abs((int(value) / 100))
    except (ValueError, ZeroDivisionError):
        return None


def send_bulk_emails(emails: list, context: Dict, tpl_filename: str) -> None:
    """
    Iterate through given emails and send email messages.
    :param emails:
    :param context:
    :param tpl_filename:
    :return:
    """
    new_emails = deepcopy(emails)
    for email in new_emails:
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        # Send email
        send_notification_email.delay(to_address=email, message=message)


def send_bulk_smses(phone_numbers: list, context: Dict, tpl_message: str) -> None:
    """
    Iterate through given emails and send sms messages.
    :param phone_numbers:
    :param context:
    :param tpl_message:
    :return:
    """
    new_phone_numbers = deepcopy(phone_numbers)
    message = tpl_message.format(**context)
    for phone_number in new_phone_numbers:
        send_notification_sms.delay(to_phone_number=phone_number, message=message)


def get_funds_senders(funds_sender: User) -> list:
    """
    Accepts user which sent funds.
    Returns list of users which related to senders account.
    Returns subusers with active statuses only.
    :return: list
    """
    account = funds_sender.account
    owner_account = account.owner_account if funds_sender.is_subuser else account
    subusers = User.objects.filter(
        Q(status=UserStatus.active),
        account__id__in=owner_account.sub_user_accounts.all().values_list("id", flat=True))
    users = [owner_account.user] + list(subusers)
    return users


def get_funds_recipients(funds_recipient: User or str) -> list:
    """
    Accepts user which got funds.
    Returns list of users which related to recipients account.
    Returns subusers with active statuses only.
    :return: list
    """
    if isinstance(funds_recipient, str):
        return [funds_recipient]
    account = funds_recipient.account
    owner_account = account.owner_account if funds_recipient.is_subuser else account
    subusers = User.objects.filter(
        Q(status=UserStatus.active),
        account__id__in=owner_account.sub_user_accounts.all().values_list("id", flat=True))
    users = [owner_account.user] + list(subusers)
    return users


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
        'sign': "-" if user == schedule.origin_user else '+'
    }
    return context


def get_ses_email_payload(tpl_filename: str, tpl_context: Dict, subject=None):
    """
    Returns email payload for sending via SES
    :param tpl_filename: for example 'notifications/email_senders_balance_updated.html'
    :param tpl_context:
    :param subject:
    :return:
    """
    new_context = deepcopy(tpl_context)
    new_context.update({
        "AWS_S3_STORAGE_BUCKET_NAME": settings.AWS_S3_STORAGE_BUCKET_NAME
    })
    message = {
        "Message": {
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': render_to_string(
                        tpl_filename,
                        context=new_context
                    ),
                },
            },
            'Subject': {
                'Charset': "UTF-8",
                'Data': subject if subject else "customate test notification.",
            },
        }
    }
    return message


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
    funds_sender = schedule.origin_user
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
