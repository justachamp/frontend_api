from __future__ import absolute_import, unicode_literals
import logging

import arrow
from celery import shared_task
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import DateField, ExpressionWrapper, F, Q

from frontend_api.models.escrow import Escrow, LoadFundsEscrowOperation, CreateEscrowOperation, EscrowOperation
from frontend_api.fields import EscrowStatus, EscrowOperationType
from frontend_api.notifications.escrows import (
    notify_about_requested_operation_status,
    notify_about_requested_operation,
    notify_about_escrow_status
)

logger = logging.getLogger(__name__)


@shared_task
def process_unaccepted_escrows():
    """
    Make sure we change escrow status to terminated if inaction of parties involved
    :return:
    """
    now = arrow.utcnow()
    expired_operations = LoadFundsEscrowOperation.objects.filter(
        Q(escrow__status=EscrowStatus.pending_funding) |
        Q(escrow__status=EscrowStatus.pending),
        approval_deadline__lte=now.datetime.date(),
        is_expired=False,
        approved__isnull=True
    )
    logger.info("Process unaccepted escrows. Expired operations count: %s" % expired_operations.count())
    paginator = Paginator(expired_operations, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for operation in paginator.page(page).object_list:  # type: LoadFundsEscrowOperation
            logger.info("Unaccepted operation id=%s and related escrow id=%s" % (operation.id, operation.escrow.id))
            # We must mark "create_escrow" operation as expired if Escrow is in "pending" state
            if operation.escrow.status is EscrowStatus.pending:
                create_escrow_operation = operation.escrow.create_escrow_operation  # type: CreateEscrowOperation
                create_escrow_operation.expire()

            # Reject initial "load_funds" operation
            operation.expire()
            operation.reject()

            # Terminate Escrow itself
            operation.escrow.move_to_status(EscrowStatus.terminated)

            escrow = operation.escrow
            creator = operation.creator
            counterpart = escrow.recipient_user if creator.id == escrow.funder_user else escrow.funder_user

            # Notify escrow counterpart about not accepted escrow
            additional_context = {'title': "the escrow wasn't funded"}
            notify_about_escrow_status(
                email_recipient=counterpart,
                counterpart=creator,
                escrow=escrow,
                additional_context=additional_context
            )


@shared_task
def reminder_to_fund_escrow():
    """
    Since each Escrow have 'funding_deadline' we're going to send two types of notifications regarding 'Funds':
        - friendly reminder ( if half time has passed )
        - final notice ( if 1 day until deadline remains )
    :return:
    """
    # Get and iterate 'half-time expired' load funds operations
    sql_query = """
        SELECT * FROM (
           SELECT *,
           ("created_at"+ ("approval_deadline" - "created_at")/2)::date AS "half_deadline",
            ROW_NUMBER() OVER (PARTITION BY escrow_id ) AS "rn"
            FROM frontend_api_escrowoperation WHERE type='load_funds' order by created_at ASC
        ) sq WHERE "rn" = 1 AND "half_deadline" = now()::date
    """

    half_time_expired_escrow_operations = LoadFundsEscrowOperation.objects.raw(sql_query)
    logger.info("Start sending friendly reminders.")
    paginator = Paginator(half_time_expired_escrow_operations, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for operation in paginator.page(page).object_list:  # type: LoadFundsEscrowOperation
            email_recipient = operation.escrow.funder_user
            counterpart = operation.escrow.recipient_user
            notify_about_requested_operation(
                email_recipient=email_recipient,
                counterpart=counterpart,
                operation=operation,
                additional_context={'operation_title': operation.type.label.lower(),
                                    'amount': operation.amount,
                                    'title': 'half time remain'}
            )

    # Get and iterate 'one day remains' load funds operations
    sql_query = """
        SELECT * FROM (
           SELECT *,
           ("frontend_api_escrowoperation"."approval_deadline" - 1)::date AS "half_deadline",
            ROW_NUMBER() OVER (PARTITION BY escrow_id ) AS "rn"
            FROM frontend_api_escrowoperation WHERE type='load_funds' order by created_at ASC
        ) sq WHERE "rn" = 1 AND "half_deadline" = now()::date
    """

    one_day_remains_escrow_operations = LoadFundsEscrowOperation.objects.raw(sql_query)
    logger.info("Start sending last notice reminders.")
    paginator = Paginator(one_day_remains_escrow_operations, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for operation in paginator.page(page).object_list:  # type: LoadFundsEscrowOperation
            email_recipient = operation.escrow.funder_user
            counterpart = operation.escrow.recipient_user
            notify_about_requested_operation(
                email_recipient=email_recipient,
                counterpart=counterpart,
                operation=operation,
                additional_context={'operation_title': operation.type.label.lower(),
                                    'amount': operation.amount,
                                    'title': 'one day remain'}
            )


@shared_task
def process_unaccepted_operations():
    """
    Make sure we change operation status to rejected if inaction of parties involved.
    Processes only escrows with 'ongoing' statuses.
    :return:
    """
    today = arrow.utcnow().datetime.date()
    expired_operations = EscrowOperation.objects.filter(
        escrow__status=EscrowStatus.ongoing,
        approval_deadline__lte=today,
        approved__isnull=True
    )
    logger.info("Process unaccepted operations. Operations count: %s" % expired_operations.count())
    paginator = Paginator(expired_operations, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for escrow_op in paginator.page(page).object_list:  # type: EscrowOperation
            operation = EscrowOperation.cast(escrow_op)
            operation.expire()
            operation.reject()

            escrow = operation.escrow
            counterpart = escrow.funder_user if operation.creator == escrow.recipient_user else escrow.recipient_user
            creator = operation.creator
            amount = escrow.balance if operation.type == EscrowOperationType.close_escrow else operation.amount

            # Send notification to operation creator
            additional_context = {
                'title': 'your request is expired',
                'amount': amount,
                'operation_title': operation.type.label.lower()
            }
            notify_about_requested_operation_status(
                email_recipient=creator,
                counterpart=counterpart,
                operation=operation,
                additional_context=additional_context
            )
