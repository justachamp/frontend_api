import logging

from celery import shared_task
from django.db import transaction
from typing import Dict

from core.logger import RequestIdGenerator
from frontend_api.models import Schedule, Escrow

logger = logging.getLogger(__name__)


@shared_task
@transaction.atomic
def on_payee_change(payee_info: Dict):
    """
    Process events from payments service.
    :param payee_info:
    :return:
    """
    logger.info("Start on_payee_change. Payee info: %s." % payee_info)
    payee_id = payee_info.get("payee_id")
    recipient_name = payee_info.get("recipient_name")
    recipient_email = payee_info.get("recipient_email")
    request_id = RequestIdGenerator.get()

    logging.init_shared_extra(request_id)
    logger.info("Received 'payee changed' event, starting processing (payee_id=%s, payee_info=%r)" % (
        payee_id, payee_info
    ), extra={
        'request_id': request_id,
        'payee_id': payee_id,
        'recipient_name': recipient_name,
        'recipient_email': recipient_email
    })

    update_schedules_payee_fields(payee_info)
    update_escrows_payee_fields(payee_info)


def update_schedules_payee_fields(payee_info: Dict):
    payee_id = payee_info.get("payee_id")
    payee_title = payee_info.get("title")
    recipient_name = payee_info.get("recipient_name")
    recipient_email = payee_info.get("recipient_email")

    logger.info("Updating schedules payee fields after receiving 'payee change' event (payee_id=%s)" % payee_id,
                extra={'payee_id': payee_id})

    if recipient_name is None or recipient_email is None or payee_title is None:
        logger.info("Some incoming payee (id=%s) data is empty, skipping update for schedules" % payee_id,
                    extra={'payee_id': payee_id})
        return

    affected_rows_count = Schedule.objects.filter(payee_id=payee_id)\
        .update(
            payee_title=payee_title,
            payee_recipient_name=recipient_name,
            payee_recipient_email=recipient_email
        )
    logger.info(f"Updated schedules (count={affected_rows_count}) for 'payee change' event (payee_id=%s)" % payee_id,
                extra={'payee_id': payee_id})


def update_escrows_payee_fields(payee_info: Dict):
    payee_id = payee_info.get("payee_id")
    recipient_name = payee_info.get("recipient_name")
    recipient_email = payee_info.get("recipient_email")

    logger.info("Updating escrows payee fields after receiving 'payee change' event (payee_id=%s)" % payee_id,
                extra={'payee_id': payee_id})

    if recipient_name is None or recipient_email is None:
        logger.info("Some incoming payee (id=%s) data is empty, skipping update for escrows" % payee_id,
                    extra={'payee_id': payee_id})
        return

    affected_rows_count = Escrow.objects.filter(payee_id=payee_id)\
        .update(
            payee_recipient_name=recipient_name,
            payee_recipient_email=recipient_email
        )
    logger.info(f"Updated escrows (count={affected_rows_count}) for 'payee change' event (payee_id=%s)" % payee_id,
                extra={'payee_id': payee_id})
