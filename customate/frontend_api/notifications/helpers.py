from typing import Dict
import logging
import arrow
from copy import deepcopy

from django.template.loader import render_to_string
from django import template
from django.conf import settings
from django.db.models import Q

from core.fields import Currency, TransactionStatusType, UserStatus
from frontend_api.models import Schedule
from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from core.models import User

logger = logging.getLogger(__name__)

register = template.Library()


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
