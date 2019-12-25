# -*- coding: utf-8 -*-

import logging
from typing import Optional, Dict

from django.conf import settings
import arrow

from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from frontend_api.notifications.helpers import get_ses_email_payload, transaction_names
from frontend_api.models.escrow import EscrowOperation, Escrow, LoadFundsEscrowOperation
from core.models import User

logger = logging.getLogger(__name__)


def notify_counterpart_about_new_escrow(counterpart: User, create_op: object, load_funds_op: object):
    """
    Once new escrow has created, send appropriate notification to counterpart.
    :param load_funds_op:
    :param counterpart:
    :param create_op:  CreateEscrowOperation object. Need for notification details.
    :return:
    """
    if counterpart.notify_by_email:
        escrow = create_op.escrow
        context = {
            "escrow": escrow,
            "create_op": create_op,
            "load_funds_op": load_funds_op
        }
        message = get_ses_email_payload(
            tpl_filename="notifications/new_escrow_created.html",
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        logger.info("Start notify about just created escrow. Counterpart: %s, Escrow id: %s" %
                    (counterpart.email, create_op.escrow.id))
        # Send email
        send_notification_email.delay(to_address=counterpart.email, message=message)


def notify_originator_about_escrow_state(counterpart: User, escrow_op: EscrowOperation, tpl_filename: str):
    """
    Once escrow has rejected / accepted by counterpart, send appropriate notification to creator.
    :param escrow_op:
    :param counterpart:
    :param tpl_filename:
    :return:
    """
    creator = escrow_op.creator
    if creator.notify_by_email:
        context = {
            "escrow": escrow_op.escrow,
            "counterpart": counterpart
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        logger.info("Start notify about escrow state. Creator: %s, context: %s" % (creator.email, context))
        send_notification_email.delay(to_address=creator.email, message=message)


def notify_about_fund_escrow_state(escrow: Escrow, transaction_info: Optional[Dict] = None):
    """
    Notify if escrow has been funded or not.
    :param escrow:
    :param transaction_info:
    :return:
    """
    recipient = escrow.recipient_user
    if recipient.notify_by_email:
        if transaction_info is None:
            context = {
                "recipient": recipient,
                "escrow": escrow
            }
            tpl_filename = "notifications/escrow_has_not_been_funded.html"
            logger.info("Start notify about funds escrow state. Escrow funded. Recipient: %s, context: %s" %
                        (recipient.email, context))
        else:
            context = {
                'amount': transaction_info.get("amount"),
                'processed_datetime': arrow.utcnow().datetime,
                'escrow': escrow,
                'transaction_type': transaction_names.get(transaction_info.get("name"), "Unknown"),
                # identifier specifies either funds has increased or decreased
                'sign': "+"
            }
            tpl_filename = "notifications/escrow_has_been_funded.html"
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        logger.info("Start notify about funds escrow state. Escrow has not been funded. Recipient: %s, context: %s" %
                    (recipient.email, context))
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
        logger.info("Start notify about requesting action with funds. Action: %s. Funder: %s" %
                    (operation.type, funder.email))
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
    recipient = escrow.recipient_user
    funder = escrow.funder_user
    now = arrow.utcnow()
    logger.info("Start notify about funds transfer. Recipient: %s, Funder: %s. Transaction info: %s." %
                (recipient.email, funder.email, transaction_info))
    context = {
        'escrow': escrow,
        'amount': amount,
        'processed_datetime': now.datetime,
        'transaction_type': transaction_names.get(transaction_info.get("name"), "Unknown"),
    }
    if recipient.notify_by_email:
        context.update({'sign': '+', 'closing_balance': 0})
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        send_notification_email.delay(to_address=recipient.email, message=message)


def send_reminder_to_fund_escrow(escrow: Escrow, tpl_filename: str):
    """
    Reminder for funding escrow by counterpart.
    :param escrow:
    :param tpl_filename:
    :return:
    """
    email_recipient = escrow.funder_user
    if email_recipient.notify_by_email:
        context = {
            "escrow": escrow
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        logger.info("Send reminder to fund escrow. Escrow id: %s." % escrow.id)
        send_notification_email.delay(to_address=email_recipient.email, message=message)


def notify_about_declined_operation_request(operation: EscrowOperation, counterpart: User, tpl_filename: str):
    """
    Requested operations may be declined.
    Sending notification about that.
    Currently sends about declined:
        - Release funds operation
    :param operation:
    :param counterpart:
    :param tpl_filename:
    :return:
    """
    recipient = operation.escrow.recipient_user
    if recipient.notify_by_email:
        context = {
            "operation": operation,
            "counterpart": counterpart
        }
        message = get_ses_email_payload(
            tpl_filename=tpl_filename,
            tpl_context=context,
            subject=settings.AWS_SES_SUBJECT_NAME
        )
        logger.info("Start notify about rejected operation request. Recipient: %s, context: %s" %
                    (recipient.email, context))
        send_notification_email.delay(to_address=recipient.email, message=message)
