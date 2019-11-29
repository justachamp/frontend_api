from __future__ import absolute_import, unicode_literals
import logging

import arrow
from celery import shared_task
from django.core.paginator import Paginator
from django.conf import settings

from frontend_api.models import Escrow, EscrowStatus

logger = logging.getLogger(__name__)


@shared_task
def process_unaccepted_escrows():
    """
    Make sure we change escrow status to terminated if inaction of parties involved
    :return:
    """
    now = arrow.utcnow()
    expired_escrows = Escrow.objects.filter(acceptance_deadline__lte=now.datetime.date())
    paginator = Paginator(expired_escrows, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        # WARN: potential generation of 1-N SQL UPDATE command here
        for escrow in paginator.page(page).object_list:
            escrow.status = EscrowStatus.terminated
            escrow.save()