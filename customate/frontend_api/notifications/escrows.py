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
            "escrow": create_op.escrow,
            "create_op": create_op
        }
        message = get_ses_email_payload(
            tpl_filename="notifications/new_escrow_created.html",
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        # Send email
        send_notification_email.delay(to_address=counterpart.email, message=message)


def notify_escrow_creator_about_escrow_state(counterpart: User, create_escrow_op: EscrowOperation, tpl_filename: str):
    """
    Once escrow has rejected / accepted by counterpart, send appropriate notification to creator.
    :param counterpart:
    :param tpl_filename:
    :param create_escrow_op: CreateEscrowOperation object. Need for notifications context.
    :return:
    """
    creator = create_escrow_op.creator
    if creator.notify_by_email:
        context = {
            "escrow": create_escrow_op.escrow,
            "counterpart": counterpart
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
            "escrow": escrow
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=recipient.email, message=message)


def notify_about_requesting_action_with_funds(counterpart: User, operation: EscrowOperation, tpl_filename: str):
    """
    Notify funder to fund escrow.
    :param operation:
    :param counterpart:
    :param tpl_filename:
    :return:
    """
    funder = operation.escrow.funder_user
    if funder.notify_by_email:
        context = {
            "operation": operation,
            "counterpart": counterpart
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=funder.email, message=message)


def notify_parties_about_funds_transfer(escrow: Escrow, tpl_filename: str, transaction_info: Dict):
    """
    While money leaves Escrow wallet, notify both recipient and funder users.
    :param tpl_filename:
    :param escrow:
    :param transaction_info:
    :return:
    """
    amount = transaction_info.get('amount')
    currency = transaction_info.get('currency')
    recipient = escrow.recipient_user
    funder = escrow.funder_user
    context = {
        'escrow': escrow,
        'amount': amount,
        'currency': currency
    }
    if recipient.notify_by_email:
        context.update({'user': recipient, 'action': 'received'})
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=recipient.email, message=message)

    if funder.notify_by_email:
        context.update({'user': funder, 'action': 'released'})
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=funder.email, message=message)


def send_reminder_to_fund_escrow(escrow: Escrow, tpl_filename: str):
    """
    Reminder for funding escrow by counterpart.
    :param escrow:
    :param tpl_filename:
    :return:
    """
    email_recipient = escrow.funder_user
    if email_recipient.notify_by_email:
        context ={
            "escrow": escrow
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=email_recipient.email, message=message)