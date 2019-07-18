from uuid import uuid4

from django.test import TestCase
from core.tests import TestUserManagementMixin
from frontend_api.core.client import PaymentApiClient
from frontend_api.models import Schedule

import logging
logger = logging.getLogger(__name__)


class ScheduleModelTest(TestCase):
    def test_calculate_and_set_total_sum_to_pay_single_payment(self):
        schedule = Schedule(number_of_payments_left=1, payment_amount=100)
        schedule.calculate_and_set_total_sum_to_pay()

        self.assertEquals(100, schedule.total_sum_to_pay)

    def test_calculate_and_set_total_sum_to_pay_several_payments(self):
        schedule = Schedule(number_of_payments_left=12, payment_amount=100)
        schedule.calculate_and_set_total_sum_to_pay()

        self.assertEquals(1200, schedule.total_sum_to_pay)

    def test_calculate_and_set_total_sum_to_pay_with_fee(self):
        schedule = Schedule(fee_amount=20, number_of_payments_left=10, payment_amount=100)
        schedule.calculate_and_set_total_sum_to_pay()

        self.assertEquals(1020, schedule.total_sum_to_pay)

    def test_calculate_and_set_total_sum_to_pay_with_fee_and_deposit(self):
        schedule = Schedule(fee_amount=20, deposit_amount=55, number_of_payments_left=10, payment_amount=100)
        schedule.calculate_and_set_total_sum_to_pay()

        self.assertEquals(1075, schedule.total_sum_to_pay)


class PaymentApiClientTest(TestCase, TestUserManagementMixin):
    def setUp(self):
        self._client = PaymentApiClient(None)

    def test_cancel_schedule_payments_not_existing_record(self):
        schedule_id = str(uuid4())
        self._client.cancel_schedule_payments(schedule_id)

        self.assertTrue(True)

    def test_get_schedule_payments_details_not_existing_record(self):
        schedule_id = str(uuid4())
        schedule_payments_details = self._client.get_schedule_payments_details(schedule_id)

        self.assertEqual(schedule_id, schedule_payments_details.schedule_id)
        self.assertEqual(0, schedule_payments_details.total_paid_sum)
