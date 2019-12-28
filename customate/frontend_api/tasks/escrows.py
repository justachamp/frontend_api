from __future__ import absolute_import, unicode_literals
import logging
from datetime import timedelta

import arrow
from celery import shared_task
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import DateField, ExpressionWrapper, F, Q

from frontend_api.models.escrow import Escrow, LoadFundsEscrowOperation
from frontend_api.fields import EscrowStatus
from frontend_api.notifications.escrows import (
    notify_about_fund_escrow_state,
    send_reminder_to_fund_escrow
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
            operation.escrow.move_to_status(EscrowStatus.terminated)
            operation.expire()
            operation.reject()
            # Send appropriate notification to seller
            notify_about_fund_escrow_state(escrow=operation.escrow)


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
    logger.info("Start sending friendly reminders. Escrows count: %d." % half_time_expired_escrow_operations.count())
    paginator = Paginator(half_time_expired_escrow_operations, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for operation in paginator.page(page).object_list:  # type: LoadFundsEscrowOperation
            send_reminder_to_fund_escrow(
                escrow=operation.escrow,
                tpl_filename="notifications/friendly_reminder_to_fund_escrow.html"
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
    logger.info("Start sending last notice reminders. Escrows count: %d." % one_day_remains_escrow_operations.count())
    paginator = Paginator(one_day_remains_escrow_operations, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for operation in paginator.page(page).object_list:  # type: LoadFundsEscrowOperation
            send_reminder_to_fund_escrow(
                escrow=operation.escrow,
                tpl_filename="notifications/final_notice_to_fund_escrow.html"
            )
