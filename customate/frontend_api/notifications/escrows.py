# -*- coding: utf-8 -*-

import logging

from django.conf import settings

from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from frontend_api.notifications.helpers import (
    prettify_number,
    send_bulk_emails,
    send_bulk_smses,
    get_funds_senders,
    get_funds_recipients,
    get_load_funds_details,
    get_schedule_details,
    get_ses_email_payload
)
from core.models import User

logger = logging.getLogger(__name__)


def notify_counterpart_about_new_escrow(counterpart: User, create_op: object):
    """
    Once new escrow has created, send appropriate notification to counterpart.
    :param counterpart:
    :param create_op:  CreateEscrowOperation object. Need for notification details.
    :return:
    """
    context = {}
    message = get_ses_email_payload(
        tpl_filename="notifications/new_escrow_created.html",
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    # Send email
    send_notification_email.delay(to_address=counterpart.email, message=message)


def notify_escrow_creator_about_rejected_escrow(create_escrow_op: object):
    """
    Once escrow has rejected by counterpart, send appropriate notification to creator.
    :param create_escrow_op: CreateEscrowOperation object. Need for notifications context.
    :return:
    """
    creator = create_escrow_op.creator
    context = {}
    message = get_ses_email_payload(
        tpl_filename="notifications/escrow_rejected_by_counterpart.html",
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    send_notification_email.delay(to_address=creator.email, message=message)
