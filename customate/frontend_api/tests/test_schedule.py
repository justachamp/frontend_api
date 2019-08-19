from unittest import skip
from uuid import uuid4
from django.test import SimpleTestCase
from rest_framework.exceptions import ValidationError
from rest_framework import status as status_codes

from core.fields import Currency, PaymentScenario, PaymentStatusType
from core.models import User
from frontend_api.core.client import PaymentApiClient, PaymentDetails
from frontend_api.fields import SchedulePeriod, ScheduleStatus
from frontend_api.models import Schedule
import arrow
import logging

logger = logging.getLogger(__name__)


class ScheduleModelTest(SimpleTestCase):
    def test_calculate_and_set_total_sum_to_pay_single_payment(self):
        schedule = Schedule(number_of_payments_left=1, payment_amount=100)
        schedule._calculate_and_set_total_sum_to_pay()

        self.assertEquals(100, schedule.total_sum_to_pay)

    def test_calculate_and_set_total_sum_to_pay_several_payments(self):
        schedule = Schedule(number_of_payments_left=12, payment_amount=100)
        schedule._calculate_and_set_total_sum_to_pay()

        self.assertEquals(1200, schedule.total_sum_to_pay)

    def test_calculate_and_set_total_sum_to_pay_with_fee(self):
        schedule = Schedule(fee_amount=20, number_of_payments_left=10, payment_amount=100)
        schedule._calculate_and_set_total_sum_to_pay()

        self.assertEquals(1020, schedule.total_sum_to_pay)

    def test_calculate_and_set_total_sum_to_pay_with_fee_and_deposit(self):
        schedule = Schedule(fee_amount=20, deposit_amount=55, number_of_payments_left=10, payment_amount=100)
        schedule._calculate_and_set_total_sum_to_pay()

        self.assertEquals(1075, schedule.total_sum_to_pay)

    def test_next_payment_date_closed_schedule(self):
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.closed, payment_amount=100)

        self.assertIsNone(schedule.next_payment_date)

    def test_next_payment_date_one_time(self):
        schedule = Schedule(period=SchedulePeriod.one_time, start_date=arrow.utcnow().datetime.date(),
                            status=ScheduleStatus.open, payment_amount=100, number_of_payments_left=1)

        self.assertEquals(schedule.start_date, schedule.next_payment_date)

    def test_next_payment_date_one_time_all_payments_made(self):
        schedule = Schedule(period=SchedulePeriod.one_time, start_date=arrow.utcnow().datetime.date(),
                            status=ScheduleStatus.open, payment_amount=100, number_of_payments_left=0)

        self.assertIsNone(schedule.next_payment_date)

    def test_next_payment_date_weekly_start_date_didnt_pass(self):
        schedule = Schedule(period=SchedulePeriod.weekly, start_date=arrow.utcnow().datetime.date(),
                            status=ScheduleStatus.open, number_of_payments_left=10, payment_amount=100)

        self.assertEquals(schedule.start_date, schedule.next_payment_date)

    def test_next_payment_date_weekly_start_date_pass(self):
        schedule = Schedule(period=SchedulePeriod.weekly, start_date=arrow.get(2013, 5, 21).datetime.date(),
                            status=ScheduleStatus.open, number_of_payments_left=10, payment_amount=100)

        self.assertEquals(arrow.get(2013, 5, 28).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_monthly(self):
        schedule = Schedule(period=SchedulePeriod.monthly, start_date=arrow.get(2013, 5, 21).datetime.date(),
                            status=ScheduleStatus.open, number_of_payments_left=10, payment_amount=100)

        self.assertEquals(arrow.get(2013, 6, 21).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_quarterly(self):
        schedule = Schedule(period=SchedulePeriod.quarterly, start_date=arrow.get(2013, 5, 21).datetime.date(),
                            status=ScheduleStatus.open, number_of_payments_left=10, payment_amount=100)

        self.assertEquals(arrow.get(2013, 9, 21).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_yearly(self):
        schedule = Schedule(period=SchedulePeriod.yearly, start_date=arrow.get(2013, 5, 21).datetime.date(),
                            status=ScheduleStatus.open, number_of_payments_left=10, payment_amount=100)

        self.assertEquals(arrow.get(2014, 5, 21).datetime.date(), schedule.next_payment_date)

    # def test_calculate_status_overdue_from_failed_payment(self):
    #     schedule = Schedule(status=ScheduleStatus.open)
    #
    #     self.assertEquals(ScheduleStatus.overdue, schedule._calculate_status(PaymentStatusType.FAILED))
    #
    # def test_calculate_status_overdue_from_refund_payment(self):
    #     schedule = Schedule(status=ScheduleStatus.open)
    #
    #     self.assertEquals(ScheduleStatus.overdue, schedule._calculate_status(PaymentStatusType.REFUND))
    #
    # def test_calculate_status_cancel_from_failed_payment(self):
    #     schedule = Schedule(status=ScheduleStatus.cancelled)
    #
    #     self.assertEquals(ScheduleStatus.cancelled, schedule._calculate_status(PaymentStatusType.FAILED))
    #
    # def test_calculate_status_cancel_from_success_payment(self):
    #     schedule = Schedule(status=ScheduleStatus.cancelled)
    #
    #     self.assertEquals(ScheduleStatus.cancelled, schedule._calculate_status(PaymentStatusType.SUCCESS))
    #
    # def test_calculate_status_closed_from_success_payment(self):
    #     schedule = Schedule(status=ScheduleStatus.open, number_of_payments_left=0)
    #
    #     self.assertEquals(ScheduleStatus.closed, schedule._calculate_status(PaymentStatusType.SUCCESS))


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

