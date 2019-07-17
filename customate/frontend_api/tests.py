from django.test import TestCase
from frontend_api.models import Schedule


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
