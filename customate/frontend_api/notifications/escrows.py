# -*- coding: utf-8 -*-

import logging
from typing import Optional, Dict

from django.conf import settings

from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from frontend_api.notifications.helpers import get_ses_email_payload
from frontend_api.models.escrow import EscrowOperation, Escrow
from core.models import User

logger = logging.getLogger(__name__)


def notify_counterpart_about_new_escrow(counterpart: User, create_op: object):
    """
    Once new escrow has created, send appropriate notification to counterpart.
    :param counterpart:
    :param create_op:  CreateEscrowOperation object. Need for notification details.
    :return:
    """
    if counterpart.notify_by_email:
        context = {
            "counterpart": counterpart.email,
            "creator": create_op.creator.email
        }
        message = get_ses_email_payload(
            tpl_filename="notifications/new_escrow_created.html",
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        # Send email
        send_notification_email.delay(to_address=counterpart.email, message=message)


def notify_escrow_creator_about_escrow_state(create_escrow_op: EscrowOperation, tpl_filename: str):
    """
    Once escrow has rejected / accepted by counterpart, send appropriate notification to creator.
    :param tpl_filename:
    :param create_escrow_op: CreateEscrowOperation object. Need for notifications context.
    :return:
    """
    creator = create_escrow_op.creator
    if creator.notify_by_email:
        context = {
            "creator": creator.email,
            "escrow_name": create_escrow_op.escrow.name
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=creator.email, message=message)


def notify_about_fund_escrow_state(escrow: Escrow, tpl_filename: str, transaction_info: Optional[Dict] = None):
    """
    Notify if escrow has been funded or not.
    :param escrow:
    :param tpl_filename:
    :param transaction_info:
    :return:
    """
    recipient = escrow.recipient_user
    if recipient.notify_by_email:
        context = {
            "recipient": recipient.email,
            "escrow_name": escrow.name
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=recipient.email, message=message)


def notify_about_requesting_action_with_funds(escrow: Escrow, tpl_filename: str):
    """
    Notify funder to fund escrow.
    :param tpl_filename:
    :param escrow:
    :return:
    """
    email_recipient = escrow.funder_user
    if email_recipient.notify_by_email:
        context = {
            "escrow_funder": email_recipient.email,
            "funds_recipient": escrow.recipient_user.email,
            "escrow_name": escrow.name
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=email_recipient.email, message=message)


