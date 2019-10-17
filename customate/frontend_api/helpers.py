# -*- coding: utf-8 -*-
from typing import Dict
import logging
import arrow
from copy import deepcopy
from django.template.loader import render_to_string
from django import template
from django.contrib.auth import get_user_model
from django.conf import settings

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


def get_funds_senders_emails(funds_sender: User) -> list:
    """
    Returns list funds senders emails
    :return: list
    """
    if funds_sender.is_owner and funds_sender.notify_by_email:
        return [funds_sender.email]
    # If funds sender is subuser owner should be notified as well
    if funds_sender.is_subuser:
        owner = funds_sender.account.owner_account.user
        emails = [user.email for user in [owner, funds_sender] if user.notify_by_email]
        return emails
    return []


def get_funds_recipients_emails(funds_recipient: User or str) -> list:
    """
    Returns list with funds recipients emails.
    :return: list
    """
    if isinstance(funds_recipient, str):
        return [funds_recipient]
    if funds_recipient.is_owner and funds_recipient.notify_by_email:
        return [funds_recipient.email]
    # If funds recipient is subuser, owner should be notified as well
    if funds_recipient.is_subuser:
        owner = funds_recipient.account.owner_account.user
        emails = [user.email for user in [funds_recipient, owner] if user.notify_by_email]
        return emails
    return []


def get_funds_senders_phones(funds_sender: User) -> list:
    """
    Returns list with funds senders phone numbers
    :return: list
    """
    phones = []
    if funds_sender.is_owner and funds_sender.notify_by_phone and funds_sender.phone_number:
        phones.append(funds_sender.phone_number)
    # If funds sender is subuser, owner should be notified as well
    if funds_sender.is_subuser:
        owner = funds_sender.account.owner_account.user
        phones.extend([user.phone_number for user in [funds_sender, owner]
                       if user.notify_by_phone and user.phone_number])
    return phones


def get_funds_recipients_phones(funds_recipient: User or str) -> list:
    """
    Returns list with funds recipients phone numbers
    :return: list
    """
    phones = []
    # If recipient is external user we cann't notify him by sms
    #   because we don't store his phone number.
    if isinstance(funds_recipient, str):
        return phones
    if funds_recipient.is_owner and funds_recipient.notify_by_phone and funds_recipient.phone_number:
        phones.append(funds_recipient.phone_number)
    # If recipient is subuser owner should be notified as well
    if funds_recipient.is_subuser:
        owner = funds_recipient.account.owner_account.user
        phones.extend([user.phone_number for user in [funds_recipient, owner]
                       if user.notify_by_phone and user.phone_number])
    return phones


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
    if schedule.purpose == SchedulePurpose.pay:
        amount = -schedule.payment_amount if schedule.origin_user == user \
            else schedule.payment_amount
    if schedule.purpose == SchedulePurpose.receive:
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
        "AWS_STORAGE_BUCKET_NAME": settings.AWS_STORAGE_BUCKET_NAME
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


def transaction_failed(schedule: Schedule, payment_info: Dict) -> None:
    """
    Sends notifications for funds sender if transaction has failed.
    :param schedule:
    :param payment_info: data from payment service.
    :return:
    """
    funds_sender = schedule.origin_user
    account_id = payment_info.get("account_id")
    logger.info("Schedule id: %s. Payment information: %s" % (schedule.id, payment_info))

    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        logger.error("Send notification (transaction failed). Account with id: %s does not exist." % account_id)
        return

    message_tpl = """ 
           Failed transaction: {amount}{cur_symbol}, 
           {dt}, 
           error={error_msg},
           {schedule_name},
           {cur_symbol} balance: {closing_balance}
       """

    if account.id in funds_sender.get_all_related_account_ids():
        closing_balance = payment_info.get("closing_balance")
        error_message = payment_info.get("error_message") or 'unknown'
        schedule_details = get_schedule_details(user=funds_sender, schedule=schedule)
        funds_senders_emails = get_funds_senders_emails(funds_sender=funds_sender)
        for email in funds_senders_emails:
            logger.info("Send email to %s: " % email)
            email_context = {"senders_closing_balance": closing_balance, **schedule_details}
            message = get_ses_email_payload(tpl_filename='notifications/email_transaction_failed.html',
                                            tpl_context=email_context)
            # send email
            send_notification_email.delay(to_address=email, message=message)

        # Extract funds senders and send sms notifications about failed transaction
        funds_senders_phones = get_funds_senders_phones(funds_sender=funds_sender)
        logger.info("Transaction failed. Schedule id: %s. Senders phones: %s" %
                    (schedule.id, ", ".join(funds_senders_phones)))
        for phone_number in funds_senders_phones:
            logger.info("Send sms to %s" % phone_number)
            message = message_tpl.format(
                amount=prettify_number(schedule_details['amount']),
                cur_symbol=schedule_details["currency"].symbol,
                dt=arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
                error_msg=error_message,
                name=schedule.name,
                closing_balance=prettify_number(closing_balance)
            )
            # send sms
            send_notification_sms.delay(to_phone_number=phone_number, message=message)


def balance_changed(schedule: Schedule, payment_info: Dict) -> None:
    """
    Send notifications for funds senders and recipients in case of successful transaction.
    :param schedule:
    :param payment_info: data from payment service.
    :return:
    """
    funds_sender = schedule.origin_user
    funds_recipient = schedule.recipient_user if schedule.recipient_user \
        else schedule.payee_recipient_email
    account_id = payment_info.get("account_id")
    logger.info("Schedule id: %s. Payment information: %s" % (schedule.id, payment_info))

    try:
        account = Account.objects.get(id=account_id)
    except Account.DoesNotExist:
        logger.error("Send notification (balance changed). Account with id: %s does not exist." % account_id)
        return

    message_tpl = """ 
        Successful transaction: {amount}{cur_symbol}, 
        {dt}, 
        {schedule_name},
        {cur_symbol} balance: {closing_balance}
    """

    # Send notifications for funds SENDERS.
    if account.id in funds_sender.get_all_related_account_ids():
        closing_balance = payment_info.get("closing_balance")
        schedule_details = get_schedule_details(user=funds_sender, schedule=schedule)
        funds_senders_emails = get_funds_senders_emails(funds_sender=funds_sender)
        for email in funds_senders_emails:
            email_context_for_senders = {"senders_closing_balance": closing_balance, **schedule_details}
            message = get_ses_email_payload(
                tpl_filename='notifications/email_senders_balance_updated.html',
                tpl_context=email_context_for_senders
            )
            # Send email
            send_notification_email.delay(to_address=email, message=message)

        funds_senders_phones = get_funds_senders_phones(funds_sender=funds_sender)
        for phone_number in funds_senders_phones:
            message = message_tpl.format(
                amount=prettify_number(schedule_details['amount']),
                cur_symbol=schedule_details["currency"].symbol,
                dt=arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
                name=schedule.name,
                closing_balance=prettify_number(closing_balance)
            )
            # send SMS
            send_notification_sms.delay(to_phone_number=phone_number, message=message)

    # Send notification for funds RECIPIENTS.
    if isinstance(funds_recipient, str):
        schedule_details = get_schedule_details(user=funds_recipient, schedule=schedule)
        message = get_ses_email_payload(
            tpl_filename='notifications/email_recipients_balance_updated.html',
            tpl_context=schedule_details
        )
        # Send email
        send_notification_email.delay(to_address=funds_recipient, message=message)
        return

    if account.id in funds_recipient.get_all_related_account_ids():
        schedule_details = get_schedule_details(user=funds_recipient, schedule=schedule)
        closing_balance = payment_info.get("closing_balance")
        funds_recipients_emails = get_funds_recipients_emails(funds_recipient=funds_recipient)
        for email in funds_recipients_emails:
            email_context_for_recipients = {'recipients_closing_balance': closing_balance, **schedule_details}
            message = get_ses_email_payload(
                tpl_filename='notifications/email_recipients_balance_updated.html',
                tpl_context=email_context_for_recipients
            )
            # Send email
            send_notification_email.delay(to_address=email, message=message)

        funds_recipients_phones = get_funds_recipients_phones(funds_recipient=funds_recipient)
        for phone_number in funds_recipients_phones:
            message = message_tpl.format(
                amount=prettify_number(schedule_details['amount']),
                cur_symbol=schedule_details["currency"].symbol,
                dt=arrow.get(schedule_details['processed_datetime']).format("YYYY/MM/DD hh:mm:ss"),
                name=schedule.name,
                closing_balance=prettify_number(closing_balance)
            )
            # Send SMS
            send_notification_sms.delay(to_phone_number=phone_number, message=message)
