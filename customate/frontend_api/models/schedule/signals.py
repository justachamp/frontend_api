# -*- coding: utf-8 -*-
from typing import Dict
import logging
import arrow

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string
from django.contrib.auth import get_user_model
from django.conf import settings

from core.fields import PaymentStatusType
from frontend_api.fields import SchedulePurpose

from .schedule import SchedulePayments, Schedule
from frontend_api.tasks import send_notification_email, send_notification_sms
from payment_api.core.client import Client
from payment_api.core.resource.models import ResourceQueryset

logger = logging.getLogger(__name__)

User = get_user_model()


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


def get_actual_balance(user: User, schedule: Schedule) -> int or None:
    """
    Function makes http request to payment service which responses with wallets data.
    Need to get user actual balance.
    :param user:
    :param schedule:
    :return:
    """
    if user and not isinstance(user, str):
        payment_api_client = Client(base_url=settings.PAYMENT_API_URL)
        queryset = ResourceQueryset('accounts', payment_api_client, 'get')
        resource = queryset.one(user.account.payment_account_id, map_attributes=True)
        wallet = [w for w in resource.wallets if w.currency == schedule.currency.value][0]
        return wallet.balance


def get_ses_email_payload(tpl_filename: str, tpl_context: Dict, subject=None):
    """
    Returns email payload for sending via SES
    :param tpl_filename: for example 'notifications/email_senders_balance_updated.html'
    :param tpl_context:
    :param subject:
    :return:
    """
    message = {
        "Message": {
            'Body': {
                'Html': {
                    'Charset': 'UTF-8',
                    'Data': render_to_string(
                        tpl_filename,
                        context=tpl_context
                    ),
                },
            },
            'Subject': {
                'Charset': "UTF-8",
                'Data': subject if subject else "Gocustomate test notification.",
            },
        }
    }
    return message


def transaction_failed(schedule):
    funds_sender = schedule.origin_user
    actual_balance = get_actual_balance(user=funds_sender, schedule=schedule)
    schedule_details = get_schedule_details(user=funds_sender, schedule=schedule)
    funds_senders_emails = get_funds_senders_emails(funds_sender=funds_sender)
    logger.info("Transaction failed. \nSchedule id: %s. Senders emails: %s" %
                (schedule.id, ", ".join(funds_senders_emails)))
    for email in funds_senders_emails:
        logger.info("Send email to %s: " % email)
        email_context = {"actual_balance": actual_balance, **schedule_details}
        message = get_ses_email_payload(tpl_filename='notifications/email_transaction_failed.html',
                                        tpl_context=email_context)
        # Pass flow control to celery task
        send_notification_email.delay(to_address=email, message=message)

    # Extract funds senders and send sms notifications about failed transaction
    funds_senders_phones = get_funds_senders_phones(funds_sender=funds_sender)
    logger.info("Transaction failed. \nSchedule id: %s. \nSenders phones: %s" %
                (schedule.id, ", ".join(funds_senders_phones)))
    for phone_number in funds_senders_phones:
        logger.info("Send sms to %s" % phone_number)
        message = 'Transaction has failed.'
        # Pass flow control to celery task
        send_notification_sms.delay(to_phone_number=phone_number, message=message)


def balance_changed(schedule):
    funds_sender = schedule.origin_user
    senders_actual_balance = get_actual_balance(user=funds_sender, schedule=schedule)
    schedule_details = get_schedule_details(user=funds_sender, schedule=schedule)
    funds_senders_emails = get_funds_senders_emails(funds_sender=funds_sender)
    for email in funds_senders_emails:
        email_context_for_senders = {"actual_balance": senders_actual_balance, **schedule_details}
        message = get_ses_email_payload(tpl_filename='notifications/email_senders_balance_updated.html',
                                        tpl_context=email_context_for_senders)
        # Pass flow control to celery task
        send_notification_email.delay(to_address=email, message=message)

    # Extract funds senders and send sms notifications about failed transaction
    funds_senders_phones = get_funds_senders_phones(funds_sender=funds_sender)
    for phone_number in funds_senders_phones:
        message = 'Transaction has failed.'
        # Pass flow control to celery task
        send_notification_sms.delay(to_phone_number=phone_number, message=message)

    funds_recipient = schedule.recipient_user if schedule.recipient_user \
        else schedule.payee_recipient_email
    schedule_details = get_schedule_details(user=funds_recipient, schedule=schedule)
    recipients_actual_balance = get_actual_balance(user=funds_recipient, schedule=schedule)
    # Extract funds recipients and send email notifications about changes in balance
    funds_recipients_emails = get_funds_recipients_emails(funds_recipient=funds_recipient)
    for email in funds_recipients_emails:
        email_context_for_recipients = {"actual_balance": recipients_actual_balance, **schedule_details}
        message = get_ses_email_payload(tpl_filename='notifications/email_recipients_balance_updated.html',
                                        tpl_context=email_context_for_recipients)
        # Pass flow control to celery task
        send_notification_email.delay(to_address=email, message=message)

    # Extract funds recipients and send sms notifications about failed transaction
    funds_recipients_phones = get_funds_recipients_phones(funds_recipient=funds_recipient)
    for phone_number in funds_recipients_phones:
        message = 'Your balance has changed.'
        # Pass flow control to celery task
        send_notification_sms.delay(to_phone_number=phone_number, message=message)


@receiver(post_save, sender=SchedulePayments)
def call_transaction_failed(sender, instance, **kwargs) -> None:
    """
    Sends email to sender if transaction has failed.
    Celery has applied.
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance.payment_status == PaymentStatusType.FAILED:
        transaction_failed(schedule=instance.schedule)


@receiver(post_save, sender=SchedulePayments)
def call_balance_changed(sender, instance, **kwargs) -> None:
    """
    Sends email and sms notifications for both sender and recipient if
        their balance has updated.
    Celery has applied
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance.payment_status == PaymentStatusType.SUCCESS:
        balance_changed(schedule=instance)
