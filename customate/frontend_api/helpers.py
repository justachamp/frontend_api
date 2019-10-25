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

from core.fields import Currency, PaymentStatusType
from frontend_api.fields import SchedulePurpose
from frontend_api.models.schedule import Schedule
from frontend_api.models import Account
from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms

logger = logging.getLogger(__name__)

User = get_user_model()

register = template.Library()


@register.filter
def prettify_number(value) -> str:
    """
    Prettifies balance number
    :param value:
    :return:
    """
    try:
        return "%0.2f" % (int(value) / 100)
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
    Returns list funds senders.
    :return: list
    """
    if funds_sender.is_owner and funds_sender.notify_by_email:
        return [funds_sender]
    # If funds sender is subuser owner should be notified as well
    if funds_sender.is_subuser:
        owner = funds_sender.account.owner_account.user
        users = [user for user in [owner, funds_sender]]
        return users
    return []


def get_funds_recipients(funds_recipient: User or str) -> list:
    """
    Returns list with funds recipients.
    :return: list
    """
    if isinstance(funds_recipient, str):
        return [funds_recipient]
    if funds_recipient.is_owner and funds_recipient.notify_by_email:
        return [funds_recipient]
    # If funds recipient is subuser, owner should be notified as well
    if funds_recipient.is_subuser:
        owner = funds_recipient.account.owner_account.user
        users = [user for user in [funds_recipient, owner]]
        return users
    return []


def get_load_funds_details(payment_info: Dict) -> Dict:
    now = arrow.utcnow()
    context = {
        "error_msg": payment_info.get("error_message") or "unknown",
        'currency': Currency(payment_info.get("currency")),
        'amount': payment_info.get("amount"),
        'processed_datetime': now.datetime,
        'recipients_closing_balance': payment_info.get("closing_balance")
    }
    return context


def get_schedule_details(user: User, schedule: Schedule) -> dict:
    """
    Retrieve context for templates with payment amount.
    For example if user paid 20$ to somebody,
        payment amount would be as "- 20$" (negative value).
        And vice versa if user got 20$, payment amount would be
        as positive number "20$".
    :param user:
    :param schedule:
    :return:
    """
    now = arrow.utcnow()
    amount = None
    # Return negative or positive value of payment amount
    if schedule.purpose == SchedulePurpose.receive:
        amount = -schedule.payment_amount if schedule.origin_user == user \
            else schedule.payment_amount
    if schedule.purpose == SchedulePurpose.pay:
        amount = schedule.payment_amount if schedule.origin_user == user \
            else -schedule.payment_amount

    context = {
        'currency': schedule.currency,
        'amount': amount,
        'processed_datetime': now.datetime,
        'additional_information': schedule.additional_information,
        'payment_type': schedule.payment_type
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


def notify_about_loaded_funds(user_id: str, payment_info: Dict, payment_status: PaymentStatusType) -> None:
    """
    Sends notification to user about updated balance after 'load funds' operation has completed.
    :param: user_id
    :param: payment_info
    :param: payment_status
    :return:
    """
    if payment_status not in [PaymentStatusType.SUCCESS, PaymentStatusType.FAILED]:
        return
    try:
        funds_recipient = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.info("User with given user_id has not found. %r" % format_exc())
        return
    logger.info("Start notify about loaded funds. Payment_info: %s" % payment_info)

    message_tpl = {
        PaymentStatusType.SUCCESS:
            ",".join(
                ["Successful transaction: {amount}{cur_symbol}",
                 "\n{dt}",
                 "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}"]
            ),
        PaymentStatusType.FAILED:
            ",".join(
                ["Failed transaction: {amount}{cur_symbol}",
                 "\n{dt}",
                 "\nReason: {error_msg}",
                 "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."]
            )
    }[payment_status]

    tpl_filename = {
        PaymentStatusType.SUCCESS: 'notifications/email_recipients_balance_updated.html',
        PaymentStatusType.FAILED: 'notifications/email_transaction_failed.html'
    }[payment_status]

    funds_recipients = get_funds_recipients(funds_recipient=funds_recipient)
    load_funds_details = get_load_funds_details(payment_info)
    emails = [user.email for user in funds_recipients if user.notify_by_email]
    logger.info("Load funds. Funds recipient emails: %s" % ", ".join(emails))
    send_bulk_emails(emails=emails,
                     context=load_funds_details,
                     tpl_filename=tpl_filename)

    sms_context = {
        "error_msg": payment_info.get("error_message") or "unknown",
        "amount": prettify_number(load_funds_details['amount']),
        "cur_symbol": load_funds_details["currency"].symbol,
        "dt": arrow.get(load_funds_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
        "closing_balance": prettify_number(load_funds_details["recipients_closing_balance"])
    }
    phone_numbers = [user.phone_number for user in funds_recipients if user.phone_number and user.notify_by_phone]
    logger.info("Load funds. Funds recipient phone numbers: %s" % ", ".join(phone_numbers))
    send_bulk_smses(phone_numbers=phone_numbers,
                    context=sms_context,
                    tpl_message=message_tpl)


def notify_about_schedules_failed_payment(schedule: Schedule, payment_info: Dict) -> None:
    """
    Sends notifications for funds sender if transaction has failed.
    :param schedule:
    :param payment_info: data from payment service.
    :return:
    """
    logger.info("Start notify about failed payment. Payment info: %s" % payment_info)
    funds_sender = schedule.origin_user
    user_id = payment_info.get("user_id")

    try:
        payment_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("User with given id not found. %r" % format_exc())
        return

    message_tpl = ",".join([
        "Failed transaction: {amount}{cur_symbol}",
        "\n{dt}",
        "\n{schedule_name}",
        "\nReason: {error_msg}",
        "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."
    ])

    if payment_user.account.id in funds_sender.get_all_related_account_ids():
        funds_senders = get_funds_senders(funds_sender=funds_sender)
        closing_balance = payment_info.get("closing_balance")
        error_message = payment_info.get("error_message") or 'unknown'
        schedule_details = get_schedule_details(user=funds_sender, schedule=schedule)
        email_context = {"senders_closing_balance": closing_balance,
                         "error_message": error_message,
                         **schedule_details}
        emails = [user.email for user in funds_senders if user.notify_by_email]
        logger.info("Failed payment. Funds senders emails: %s ." % ", ".join(emails))
        send_bulk_emails(emails=emails,
                         context=email_context,
                         tpl_filename='notifications/email_transaction_failed.html')

        # Extract funds senders and send sms notifications about failed transaction
        sms_context = {
            "amount": prettify_number(schedule_details['amount']),
            "cur_symbol": schedule_details["currency"].symbol,
            "dt": arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
            "error_msg": error_message,
            "schedule_name": schedule.name if len(schedule.name) < 20 else schedule.name[:20] + '...',
            "closing_balance": prettify_number(closing_balance)
        }
        phone_numbers = [user.phone_number for user in funds_senders if user.phone_number and user.notify_by_phone]
        logger.info("Failed payment. Funds senders phone numbers: %s ." % ", ".join(phone_numbers))
        send_bulk_smses(phone_numbers=phone_numbers,
                        context=sms_context,
                        tpl_message=message_tpl)
    else:
        logger.info("Failed payment. Notifications sending has passed. Schedule id: %s" % schedule.id)


def notify_about_schedules_successful_payment(schedule: Schedule, payment_info: Dict) -> None:
    """
    Send notifications for funds senders and recipients in case of successful transaction.
    :param schedule:
    :param payment_info: data from payment service.
    :return:
    """
    logger.info("Start notify about successful payment. Payment info: %s" % payment_info)
    funds_sender = schedule.origin_user
    funds_recipient = schedule.recipient_user if schedule.recipient_user \
        else schedule.payee_recipient_email
    user_id = payment_info.get("user_id")
    try:
        payment_user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.error("User with given id not found. %r" % format_exc())
        return

    outgoing_payment_message_tpl = ",".join([
        "Successful transaction: - {amount}{cur_symbol}",
        "\n{dt}",
        "\n{schedule_name}",
        "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}."
    ])

    # Send notifications for funds SENDERS.
    if payment_user.account.id in funds_sender.get_all_related_account_ids():
        funds_senders = get_funds_senders(funds_sender=funds_sender)
        closing_balance = payment_info.get("closing_balance")
        schedule_details = get_schedule_details(user=funds_sender, schedule=schedule)
        email_context_for_senders = {"senders_closing_balance": closing_balance, **schedule_details}
        emails = [user.email for user in funds_senders if user.notify_by_email]
        logger.info("Successful payment. Funds senders emails: %s" % ", ".join(emails))
        send_bulk_emails(emails=emails,
                         context=email_context_for_senders,
                         tpl_filename='notifications/email_senders_balance_updated.html')
        sms_context = {
            "amount": prettify_number(schedule_details['amount']),
            "cur_symbol": schedule_details["currency"].symbol,
            "dt": arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
            "schedule_name": schedule.name if len(schedule.name) < 20 else schedule.name[:20] + '...',
            "closing_balance": prettify_number(closing_balance)
        }
        phone_numbers = [user.phone_number for user in funds_senders if user.phone_number and user.notify_by_phone]
        logger.info("Successful payment. Funds senders phone_numbers: %s" % ", ".join(phone_numbers))
        send_bulk_smses(phone_numbers=phone_numbers,
                        context=sms_context,
                        tpl_message=outgoing_payment_message_tpl)

    # Send notification for funds RECIPIENTS.
    if isinstance(funds_recipient, str):
        logger.info("Successful payment. External recipient: %s" % funds_recipient)
        schedule_details = get_schedule_details(user=funds_recipient, schedule=schedule)
        message = get_ses_email_payload(
            tpl_filename='notifications/email_recipients_balance_updated.html',
            tpl_context=schedule_details,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        # Send email
        send_notification_email.delay(to_address=funds_recipient, message=message)
        return

    incoming_payment_message_tpl = ",".join([
        "Successful transaction: + {amount}{cur_symbol}",
        "\n{dt}",
        "\n{payment_type}",
        "\n{cur_symbol} wallet available balance: {closing_balance} {cur_symbol}"
    ])

    if payment_user.account.id in funds_recipient.get_all_related_account_ids():
        funds_recipients = get_funds_recipients(funds_recipient=funds_recipient)
        schedule_details = get_schedule_details(user=funds_recipient, schedule=schedule)
        closing_balance = payment_info.get("closing_balance")
        email_context_for_recipients = {'recipients_closing_balance': closing_balance, **schedule_details}
        emails = [user.email for user in funds_recipients if user.notify_by_email]
        logger.info("Successful payment. Funds recipient emails: %s" % ", ".join(emails))
        send_bulk_emails(emails=emails,
                         context=email_context_for_recipients,
                         tpl_filename='notifications/email_recipients_balance_updated.html')

        sms_context = {
            "payment_type": schedule.payment_type,
            "amount": prettify_number(schedule_details['amount']),
            "cur_symbol": schedule_details["currency"].symbol,
            "dt": arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
            "schedule_name": schedule.name if len(schedule.name) < 20 else schedule.name[:20] + '...',
            "closing_balance": prettify_number(closing_balance)
        }
        phone_numbers = [user.phone_number for user in funds_recipients if user.phone_number and user.notify_by_phone]
        logger.info("Successful payment. Funds recipient phone numbers: %s" % ", ".join(phone_numbers))
        send_bulk_smses(phone_numbers=phone_numbers,
                        context=sms_context,
                        tpl_message=incoming_payment_message_tpl)
        logger.info("Successful payment. Notifications sent to all participants. Schedule id: %s " % schedule.id)
    else:
        logger.info("Successful payment. Notifications sending has passed.")
