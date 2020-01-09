# -*- coding: utf-8 -*-

import logging
from typing import Optional, Dict

from django.conf import settings
import arrow

from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from frontend_api.notifications.helpers import get_ses_email_payload, transaction_names
from frontend_api.models.escrow import EscrowOperation, Escrow, LoadFundsEscrowOperation
from core.models import User
from core.fields import PayeeType
from external_apis.payment import service as payment_service
from frontend_api.notifications.helpers import get_load_funds_details

logger = logging.getLogger(__name__)


def notify_about_fund_escrow_state(escrow: Escrow, transaction_info: Optional[Dict] = None):
    """
    Notify if escrow has been funded or not.
    :param escrow:
    :param transaction_info:
    :return:
    """
    recipient = escrow.recipient_user
    if transaction_info is None:
        context = {
            "recipient": recipient,
            "escrow": escrow
        }
        tpl_filename = "notifications/escrow_has_not_been_funded.html"
        logger.info("Start notify about funds escrow state. Escrow has not been funded. Recipient: %s, context: %s" %
                    (recipient.email, context))
    else:
        context = {
            'amount': transaction_info.get("amount"),
            'processed_datetime': arrow.utcnow().datetime,
            'escrow': escrow,
            'transaction_name': transaction_names.get(transaction_info.get("name"), "Unknown"),
            # identifier specifies either funds has increased or decreased
            'sign': "+"
        }
        tpl_filename = "notifications/escrow/escrow_has_been_funded.html"
    message = get_ses_email_payload(
        tpl_filename=tpl_filename,
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    logger.info("Start notify about funds escrow state. Recipient: %s, Transaction info: %s" %
                (recipient.email, transaction_info))
    send_notification_email.delay(to_address=recipient.email, message=message)


def notify_escrow_funder_about_transaction_status(escrow: Escrow, transaction_info: Dict,
                                                  tpl_filename: str, additional_context: Dict = None):
    """
    Handles two types of transactions: from Wallet to Escrow, from Escrow to recipients Wallet.
    Sending notifications about successful or failed transactions.
    :param additional_context: need for specifying should balance be for Wallet or Escrow
    :param escrow:
    :param transaction_info:
    :param tpl_filename:
    :return:
    """
    funder = escrow.funder_user
    context = get_load_funds_details(transaction_info)
    context.update({"name": escrow.name})
    if additional_context:
        # Replace "Wallet" name to "Escrow" in template
        # View escrow balance as balance (variable name in common template)
        context.update(additional_context)
        context["closing_balance"] = escrow.balance

    message = get_ses_email_payload(
        tpl_filename=tpl_filename,
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    logger.info("Start notify funder about transaction status. "
                "Funder: %s, Transaction_info: %s. Escrow: %s. Context: %s" %
                (funder.email, transaction_info, escrow.id, context))
    send_notification_email.delay(to_address=funder.email, message=message)


def notify_about_requested_operation_status(email_recipient: User, counterpart: User,
                                            operation: EscrowOperation, additional_context: Dict):
    """
    Notify operation creator about operation request state (either accepted or rejected).
    :param email_recipient:
    :param counterpart:
    :param operation:
    :param additional_context:
    :return:
    """
    tpl_filename = "notifications/escrow/requested_operation_status.html"
    context = {
        "operation_obj": operation,
        "counterpart": counterpart
    }
    context.update(additional_context)
    message = get_ses_email_payload(
        tpl_filename=tpl_filename,
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    logger.info(
        "Start notify about operation request state. Email recipient: %s, context: %s" % (email_recipient, context))
    send_notification_email.delay(to_address=email_recipient.email, message=message)


def notify_about_requested_operation(email_recipient: User, counterpart: User,
                                     operation: EscrowOperation, additional_context: Dict):
    """
    Handle all requests to counterpart. Sending notifications about proposed operation (load funds, release funds etc.)
    :param: email_recipient
    :param: counterpart
    :param: operation
    :param: additional_context
    :return:
    """
    tpl_filename = "notifications/escrow/requesting_operation.html"
    context = {
        "operation_obj": operation,
        "counterpart": counterpart
    }
    context.update(additional_context)
    message = get_ses_email_payload(
        tpl_filename=tpl_filename,
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    logger.info("Start notify about requested operation. Email recipient: %s. Context: %s" % (email_recipient, context))
    send_notification_email.delay(to_address=email_recipient.email, message=message)


def notify_about_escrow_status(email_recipient: User, counterpart: User,
                               escrow: Escrow, additional_context: Dict):
    """
    Handle all requests to counterpart. Sending notifications about proposed operation (load funds, release funds etc.)
    :param: email_recipient
    :param: counterpart
    :param: escrow
    :param: additional_context
    :return:
    """
    tpl_filename = "notifications/escrow/escrow_status.html"
    context = {
        "escrow": escrow,
        "counterpart": counterpart
    }
    context.update(additional_context)
    message = get_ses_email_payload(
        tpl_filename=tpl_filename,
        tpl_context=context,
        subject=settings.AWS_SES_SUBJECT_NAME
    )
    logger.info(
        "Start notify about requested operation status. Email recipient: %s. Context: %s" % (email_recipient, context)
    )
    send_notification_email.delay(to_address=email_recipient.email, message=message)
