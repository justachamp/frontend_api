from unittest import skip
from uuid import uuid4
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework import status as status_codes

from core.fields import Currency
from core.models import User
from frontend_api.core.client import PaymentApiClient, PaymentDetails
import logging

logger = logging.getLogger(__name__)


@skip("Waiting for mocks")
class PaymentApiClientTest(SimpleTestCase):
    def setUp(self):
        self._client = PaymentApiClient(User(id=str(uuid4())))

    def test_cancel_schedule_payments_not_existing_record(self):
        schedule_id = str(uuid4())
        self._client.cancel_schedule_payments(schedule_id)

        self.assertTrue(True)

    def test_force_payment(self):
        payment_id = str(uuid4())

        with self.assertRaises(ValidationError) as e:
            self._client.force_payment(payment_id)

        self.assertEqual(e.exception.status_code, status_codes.HTTP_400_BAD_REQUEST)

    def test_create_payment(self):
        payment_details = PaymentDetails(
            user_id=uuid4(),
            payment_account_id=uuid4(),
            schedule_id=uuid4(),
            currency=Currency.EUR,
            amount=10,
            description='',
            payee_id=uuid4(),
            funding_source_id=uuid4()
        )

        with self.assertRaises(ValidationError) as e:
            self._client.create_payment(payment_details)

        self.assertEqual(e.exception.status_code, status_codes.HTTP_400_BAD_REQUEST)