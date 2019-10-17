from __future__ import absolute_import, unicode_literals
from traceback import format_exc
import logging
from celery import shared_task
from django.conf import settings

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

logger = logging.getLogger(__name__)



@shared_task
def send_notification_email(to_address, message):
    email_client = boto3.client('ses', aws_access_key_id=settings.AWS_ACCESS_KEY,
                                aws_secret_access_key=settings.AWS_SECRET_KEY,
                                region_name=settings.AWS_REGION_SES)
    kwargs = {
        "Source": settings.AWS_SES_NOTIFICATIONS_GOCUSTOMATE_SENDER,
        "Destination": {
            "ToAddresses": [to_address]
        }
    }
    try:
        email_client.send_email(**kwargs, **message)
    except (ClientError, EndpointConnectionError):
        logger.error("Error while sending email via boto3 with outcoming data: %s. %r" % (kwargs, format_exc()))


@shared_task
def send_notification_sms(to_phone_number, message):
    sms_client = boto3.client('sns', aws_access_key_id=settings.AWS_ACCESS_KEY,
                              aws_secret_access_key=settings.AWS_SECRET_KEY,
                              region_name=settings.AWS_REGION_SNS)
    kwargs = {"PhoneNumber": to_phone_number,
              "Message": message}
    try:
        sms_client.publish(**kwargs)
    except:
        logger.error("Unable to send message via boto3 with outcoming data: %s. %r" % (kwargs, format_exc()))
