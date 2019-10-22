from __future__ import absolute_import, unicode_literals
from datetime import timedelta
import logging
from traceback import format_exc

import arrow
from celery import shared_task
from botocore.exceptions import ClientError
from requests import delete as delete_http_request
from requests.exceptions import RequestException
from django.core.paginator import Paginator
from django.conf import settings

from frontend_api.models import Schedule, Document
from frontend_api.fields import ScheduleStatus, SchedulePurpose

logger = logging.getLogger(__name__)


@shared_task
def process_unaccepted_schedules():
    """
    Make sure we change schedules status to rejected
        if this schedule was not accepted by payer before deposit_payment_date (if not None) or start_date
    :return:
    """
    now = arrow.utcnow()
    opened_receive_funds_schedules = Schedule.objects.filter(
        purpose=SchedulePurpose.receive,
        status=ScheduleStatus.open
    )
    # Filter opened receive funds schedules by deposit_payment_date (if not None) or start_date
    schedules_with_deposit_payment_date = opened_receive_funds_schedules.filter(
        deposit_payment_date__isnull=False).filter(
        deposit_payment_date__lt=now.datetime)
    schedules_without_deposit_payment_date = opened_receive_funds_schedules.filter(
        deposit_payment_date__isnull=True,
        start_date__lt=now.datetime)
    unaccepted_schedules = schedules_with_deposit_payment_date | schedules_without_deposit_payment_date

    paginator = Paginator(unaccepted_schedules, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        # Update statuses via .move_to_status()
        # WARN: potential generation of 1-N SQL UPDATE command here
        for schedule in paginator.page(page).object_list:
            schedule.move_to_status(ScheduleStatus.rejected)


@shared_task
def remove_unassigned_documents():
    """
    Remove all documents which not related with any schedule.
    :return:
    """
    hour_ago = arrow.utcnow().datetime - timedelta(hours=1)

    # Documents without related schedule which created more than hour ago
    outdated_documents = Document.objects.filter(schedule=None, created_at__lte=hour_ago, key__isnull=False)

    paginator = Paginator(outdated_documents, settings.CELERY_BEAT_PER_PAGE_OBJECTS)
    for page in paginator.page_range:
        for document in paginator.page(page).object_list:  # type: Document
            # Get presigned url for deleting document
            try:
                delete_url = document.generate_s3_presigned_url(operation_name='delete_object')
            except ClientError as e:
                logger.error("AWS S3 service is unavailable %r" % format_exc())
                return
            # Make delete request with gotten url
            try:
                delete_http_request(delete_url)
            except RequestException:
                logger.error("S3 connection error during removing file %r" % format_exc())
                return
            # Remove appropriate relation from database.
            document.delete()
