from unittest import skip
import boto3

from django.contrib.auth import get_user_model
from django.test import SimpleTestCase
from django.conf import settings
from django.template.loader import render_to_string

from core.fields import PaymentStatusType
from frontend_api.helpers import notify_about_loaded_funds


@skip("rewrite without actual requests to AWS")
class TestEmailNotifier(SimpleTestCase):
    """
    Test if email notifier works.
    Celery server is not applied!
    """

    def setUp(self):
        self.client = boto3.client('ses', aws_access_key_id=settings.AWS_ACCESS_KEY,
                                   aws_secret_access_key=settings.AWS_SECRET_KEY,
                                   region_name=settings.AWS_REGION_SNS)

        self.test_recipient = "test_recipient@gocustomate.com"
        self.domain_sender = settings.AWS_SES_NOTIFICATIONS_GOCUSTOMATE_SENDER

    def test_if_email_notifier_sends_emails(self):
        data = {
            "Source": self.domain_sender,
            "Destination": {
                "ToAddresses": [self.test_recipient]
            }
        }
        message = {
            "Message": {
                'Body': {
                    'Html': {
                        'Charset': 'UTF-8',
                        'Data': render_to_string(
                            "notifications/email_senders_balance_updated.html",
                            context={"header": "Dummy template", "data": "Test info block."}
                        ),
                    },
                },
                'Subject': {
                    'Charset': "UTF-8",
                    'Data': "Gocustomate test notification.",
                },
            }
        }
        response = self.client.send_email(**message, **data)
        self.assertEqual(200, response["ResponseMetadata"].get("HTTPStatusCode"))


@skip("rewrite without actual requests to AWS")
class TestSmsNotifier(SimpleTestCase):
    """
    Test if sms notifier works.
    Celery server is not applied!
    """

    def setUp(self):
        self.client = boto3.client('sns', aws_access_key_id=settings.AWS_ACCESS_KEY,
                                   aws_secret_access_key=settings.AWS_SECRET_KEY,
                                   region_name=settings.AWS_REGION_SNS)
        self.test_recipient = '+447365035690'

    def test_if_sms_notifier_sends_smses(self):
        data = {"PhoneNumber": self.test_recipient,
                "Message": "Test sms from customate."}
        response = self.client.publish(**data)
        self.assertEqual(200, response["ResponseMetadata"].get("HTTPStatusCode"))

