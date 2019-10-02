# -*- coding: utf-8 -*-
from typing import Dict
import logging

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.loader import render_to_string

from core.fields import PaymentStatusType

from .schedule import SchedulePayments, Schedule
from frontend_api.tasks import send_notification_email, send_notification_sms

logger = logging.getLogger(__name__)


def get_funds_senders_emails(schedule: Schedule) -> list:
    """
    Returns list funds senders emails
    :return: list
    """
    sender = schedule.origin_user  # funds sender
    if sender.is_owner and sender.notify_by_email:
        return [sender.email]
    # If funds sender is subuser owner should be notified as well
    if sender.is_subuser:
        owner = sender.account.owner_account.user
        emails = [user.email for user in [owner, sender] if user.notify_by_email]
        return emails
    return []


def get_funds_recipients_emails(schedule: Schedule) -> list:
    """
    Returns list with funds recipients emails.
    :return: list
    """
    recipient = schedule.recipient_user  # funds recipient
    if not recipient:
        return [schedule.payee_recipient_email]
    if recipient.is_owner and recipient.notify_by_email:
        return [recipient.email]
    # If funds recipient is subuser, owner should be notified as well
    if recipient.is_subuser:
        owner = recipient.account.owner_account.user
        emails = [user.email for user in [recipient, owner] if user.notify_by_email]
        return emails
    return []


def get_funds_senders_phones(schedule: Schedule) -> list:
    """
    Returns list with funds senders phone numbers
    :return: list
    """
    phones = []
    sender = schedule.origin_user  # funds sender
    if sender.is_owner and sender.notify_by_phone and sender.phone_number:
        phones.append(sender.phone_number)
    # If funds sender is subuser, owner should be notified as well
    if sender.is_subuser:
        owner = sender.account.owner_account.user
        phones.extend([user.phone_number for user in [sender, owner] if user.notify_by_phone and user.phone_number])
    return phones


def get_funds_recipients_phones(schedule: Schedule) -> list:
    """
    Returns list with funds recipients phone numbers
    :return: list
    """
    phones = []
    recipient = schedule.recipient_user  # funds recipient
    # If recipient is external user we cann't notify him by sms
    #   because we don't store his phone number.
    if not recipient:
        return phones
    if recipient.is_owner and recipient.notify_by_phone and recipient.phone_number:
        phones.append(recipient.phone_number)
    # If recipient is subuser owner should be notified as well
    if recipient.is_subuser:
        owner = recipient.account.owner_account.user
        phones.extend([user.phone_number for user in [recipient, owner] if user.notify_by_phone and user.phone_number])
    return phones


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


@receiver(post_save, sender=SchedulePayments)
def transaction_failed(sender, instance, **kwargs) -> None:
    """
    Sends email to sender if transaction has failed.
    Celery has applied.
    :param sender:
    :param instance:
    :param kwargs:
    :return:
    """
    if instance.payment_status == PaymentStatusType.FAILED:
        # Extract funds senders and send email notifications about failed transaction
        funds_senders_emails = get_funds_senders_emails(schedule=instance.schedule)
        logger.info("Transaction failed. \nSchedule id: %s. Senders emails: %s" %
                    (instance.schedule.id, ", ".join(funds_senders_emails)))
        for email in funds_senders_emails:
            logger.info("Send email to %s: " % email)
            context = {'original_amount': instance.original_amount, 'payment_id': instance.payment_id}
            message = get_ses_email_payload(tpl_filename='notifications/email_transaction_failed.html',
                                            tpl_context=context)
            # Pass flow control to celery task
            send_notification_email.delay(to_address=email, message=message)

        # Extract funds senders and send sms notifications about failed transaction
        funds_senders_phones = get_funds_senders_phones(schedule=instance.schedule)
        logger.info("Transaction failed. \nSchedule id: %s. \nSenders phones: %s" %
                    (instance.schedule.id, ", ".join(funds_senders_phones)))
        for phone_number in funds_senders_phones:
            logger.info("Send sms to %s" % phone_number)
            message = 'Transaction has failed.'
            # Pass flow control to celery task
            send_notification_sms.delay(to_phone_number=phone_number, message=message)



@receiver(post_save, sender=SchedulePayments)
def balance_changed(sender, instance, **kwargs) -> None:
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
        # Extract funds senders and send email notifications about changes in balance
        funds_senders_emails = get_funds_senders_emails(schedule=instance.schedule)
        for email in funds_senders_emails:
            context = {'original_amount': instance.original_amount, 'payment_id': instance.payment_id}
            message = get_ses_email_payload(tpl_filename='notifications/email_senders_balance_updated.html',
                                            tpl_context=context)
            # Pass flow control to celery task
            send_notification_email.delay(to_address=email, message=message)

        # Extract funds senders and send sms notifications about failed transaction
        funds_senders_phones = get_funds_senders_phones(schedule=instance.schedule)
        for phone_number in funds_senders_phones:
            message = 'Your balance has changed.'
            # Pass flow control to celery task
            send_notification_sms.delay(to_phone_number=phone_number, message=message)

        # Extract funds recipients and send email notifications about changes in balance
        funds_recipients_emails = get_funds_recipients_emails(schedule=instance.schedule)
        for email in funds_recipients_emails:
            context = {'original_amount': instance.original_amount, 'payment_id': instance.payment_id}
            message = get_ses_email_payload(tpl_filename='notifications/email_recipients_balance_updated.html',
                                            tpl_context=context)
            # Pass flow control to celery task
            send_notification_email.delay(to_address=email, message=message)

        # Extract funds recipients and send sms notifications about failed transaction
        funds_recipients_phones = get_funds_recipients_phones(schedule=instance.schedule)
        for phone_number in funds_recipients_phones:
            message = 'Your balance has changed.'
            # Pass flow control to celery task
            send_notification_sms.delay(to_phone_number=phone_number, message=message)
