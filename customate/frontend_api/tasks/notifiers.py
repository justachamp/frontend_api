from __future__ import absolute_import, unicode_literals
from traceback import format_exc
import logging

from celery import shared_task
from django.conf import settings
from botocore.exceptions import ClientError, EndpointConnectionError
from external_apis.aws.service import get_aws_client

logger = logging.getLogger(__name__)


@shared_task
def send_notification_email(to_address, message):
    logger.info("Send email notification to %s" % to_address)
    email_client = get_aws_client('ses', region_name=settings.AWS_REGION_SES)
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
    logger.info("Send sms notification to %s " % to_phone_number)
    sms_client = get_aws_client('sns', region_name=settings.AWS_REGION_SNS)
    kwargs = {"MessageAttributes": {
        'AWS.SNS.SMS.SMSType': {
            'DataType': 'String',
            'StringValue': 'Transactional'},
        'AWS.SNS.SMS.SenderID': {
            'DataType': 'String',
            'StringValue': settings.AWS_SNS_NOTIFICATIONS_GOCUSTOMATE_SENDER,
        }
    },
        "PhoneNumber": to_phone_number,
        "Message": message}
    try:
        sms_client.publish(**kwargs)
    except:
        logger.error("Unable to send message via boto3 with outcoming data: %s. %r" % (kwargs, format_exc()))
