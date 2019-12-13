from __future__ import absolute_import, unicode_literals
import logging

import arrow
from celery import shared_task
from django.core.paginator import Paginator
from django.conf import settings
from django.db.models import Q

from frontend_api.models.escrow import LoadFundsEscrowOperation
from frontend_api.fields import EscrowStatus
from frontend_api.notifications.escrows import notify_about_fund_escrow_state

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
            operation.escrow.move_to_status(EscrowStatus.terminated)
            operation.expire()
            operation.reject()
            # Send appropriate notification to seller
            notify_about_fund_escrow_state(
                escrow=operation.escrow,
                tpl_filename="notifications/escrow_has_not_been_funded.html"
            )
