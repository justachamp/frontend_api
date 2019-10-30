from unittest import skip
from uuid import uuid4
import arrow
import logging

from django.test import SimpleTestCase, TestCase
from rest_framework.exceptions import ValidationError
from rest_framework import status as status_codes

from core.fields import FundingSourceType, Currency, PayeeType, PaymentStatusType
from core.models import User
from frontend_api.core.client import PaymentApiClient, PaymentDetails
from frontend_api.fields import SchedulePeriod, ScheduleStatus, SchedulePurpose, AccountType
from frontend_api.models import Schedule, UserAccount


from frontend_api.models.schedule import DepositsSchedule, OnetimeSchedule, WeeklySchedule, SchedulePayments

logger = logging.getLogger(__name__)


class ScheduleModelTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('test_user')
        UserAccount(account_type=AccountType.personal, user=cls.user).save()

    @staticmethod
    def _get_test_schedule_model():
        return Schedule(start_date=arrow.utcnow().datetime.date(), payment_amount=100, purpose=SchedulePurpose.receive,
                        status=ScheduleStatus.open, currency=Currency.EUR, payee_id=uuid4(), payee_type=PayeeType.WALLET,
                        number_of_payments=10, funding_source_id=uuid4(), origin_user_id=ScheduleModelTest.user.id,
                        recipient_user_id=ScheduleModelTest.user.id)

    @staticmethod
    def _get_test_schedulepayment_model(schedule: Schedule, payment_status: PaymentStatusType):
        return SchedulePayments(
            schedule_id=schedule.id,
            payment_id=uuid4(),
            funding_source_id=schedule.funding_source_id,
            parent_payment_id=None,
            payment_status=payment_status,
            original_amount=schedule.payment_amount
        )

    def test_next_payment_date_closed_schedule(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.one_time
        schedule.status = ScheduleStatus.closed
        schedule.number_of_payments = 1
        schedule.save()

        self.assertIsNone(schedule.next_payment_date)

    def test_next_payment_date_one_time(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.one_time
        schedule.number_of_payments = 1
        schedule.save()

        self.assertEquals(schedule.start_date, schedule.next_payment_date)

    def test_next_payment_date_weekly_start_date_is_current_date(self):
        current_datetime = arrow.utcnow()
        schedule = self._get_test_schedule_model()
        schedule.start_date = current_datetime.datetime.date()
        schedule.period = SchedulePeriod.weekly
        schedule.save()

        self.assertEquals(current_datetime.shift(weeks=1).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_weekly_start_date_pass(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.get(2013, 5, 21).datetime.date()
        schedule.period = SchedulePeriod.weekly
        schedule.save()

        self.assertEquals(arrow.get(2013, 5, 28).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_weekly_two_made_payments(self):
        current_datetime = arrow.utcnow()
        schedule = self._get_test_schedule_model()
        schedule.start_date = current_datetime.datetime.date()
        schedule.period = SchedulePeriod.weekly
        schedule.number_of_payments_made = 2
        schedule.save()

        self.assertEquals(current_datetime.shift(weeks=2).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_monthly(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.get(2013, 5, 21).datetime.date()
        schedule.period = SchedulePeriod.monthly
        schedule.save()

        self.assertEquals(arrow.get(2013, 6, 21).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_quarterly(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.get(2013, 5, 21).datetime.date()
        schedule.period = SchedulePeriod.quarterly
        schedule.save()

        self.assertEquals(arrow.get(2013, 9, 21).datetime.date(), schedule.next_payment_date)

    def test_next_payment_date_yearly(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.get(2013, 5, 21).datetime.date()
        schedule.period = SchedulePeriod.yearly
        schedule.save()

        self.assertEquals(arrow.get(2014, 5, 21).datetime.date(), schedule.next_payment_date)

    def test_have_time_for_deposit_payment_processing_no_deposit(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.weekly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self.assertTrue(schedule.have_time_for_deposit_payment_processing_by_scheduler)

    def test_have_time_for_deposit_payment_processing__deposit_in_future(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.weekly
        schedule.deposit_payment_date = arrow.utcnow().shift(days=10).datetime.date()
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self.assertTrue(schedule.have_time_for_deposit_payment_processing_by_scheduler)

    """
        We changed funding source to CREDIT_CARD: 
        there is NO time for deposit payment 
    """
    def test_have_time_for_deposit_payment_processing__deposit_in_past(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.weekly
        schedule.deposit_payment_date = arrow.utcnow().shift(days=4).datetime.date()
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self.assertFalse(schedule.have_time_for_deposit_payment_processing_by_scheduler)

    """
        We changed funding source to CREDIT_CARD, but deposit payment was already executed in past 
    """
    def test_have_time_for_deposit_payment_processing__deposit_was_executed_in_past(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.weekly
        schedule.deposit_payment_date = arrow.utcnow().shift(days=-10).datetime.date()
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        schedule_payment = self._get_test_schedulepayment_model(schedule, PaymentStatusType.SUCCESS)
        schedule_payment.is_deposit = True
        schedule_payment.save()

        self.assertTrue(schedule.have_time_for_deposit_payment_processing_by_scheduler)

    def test_have_time_for_regular_payment_processing__weekly_execution_date_in_future(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.utcnow().shift(days=10).datetime.date()
        schedule.period = SchedulePeriod.weekly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.SUCCESS).save()

        self.assertTrue(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made first, weekly payment today and changed funding source to CREDIT_CARD: 
        there is NO time for nearest payment
    """
    def test_have_time_for_regular_payment_processing__weekly_execution_date_today_have_no_time(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.weekly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.PROCESSING).save()

        self.assertFalse(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made first, weekly payment yesterday and changed funding source to CREDIT_CARD: 
        there is NO time for nearest payment
    """
    def test_have_time_for_regular_payment_processing__weekly_execution_date_in_past_have_no_time(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.utcnow().shift(days=-1).datetime.date()
        schedule.period = SchedulePeriod.weekly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.PROCESSING).save()

        self.assertFalse(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made first, monthly payment today and changed funding source to CREDIT_CARD: 
        there is time for nearest payment
    """
    def test_have_time_for_regular_payment_processing__monthly_execution_date_today_have_time(self):
        schedule = self._get_test_schedule_model()
        schedule.period = SchedulePeriod.monthly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.PROCESSING).save()

        self.assertTrue(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made first, monthly payment 10 days ago and changed funding source to CREDIT_CARD: 
        there is time for nearest payment
    """
    def test_have_time_for_regular_payment_processing__monthly_execution_date_in_past_have_time(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.utcnow().shift(days=-10).datetime.date()
        schedule.period = SchedulePeriod.monthly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.PROCESSING).save()

        self.assertTrue(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made first, monthly payment 28 days ago and changed funding source to CREDIT_CARD: 
        there is NO time for nearest payment
    """
    def test_have_time_for_regular_payment_processing__monthly_execution_date_in_past_have_no_time(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.utcnow().shift(days=-28).datetime.date()
        schedule.period = SchedulePeriod.monthly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.PROCESSING).save()

        self.assertFalse(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made two monthly payments 2 months and 3 days ago and changed funding source to CREDIT_CARD: 
        there is NO time for nearest payment
    """
    def test_have_time_for_regular_payment_processing__monthly_execution_date_in_past_have_no_time_for_third_payment(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.utcnow().shift(months=-2, days=-3).datetime.date()
        schedule.period = SchedulePeriod.monthly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.SUCCESS).save()
        self._get_test_schedulepayment_model(schedule, PaymentStatusType.PROCESSING).save()

        self.assertFalse(schedule.have_time_for_regular_payment_processing_by_scheduler)

    """
        We made first, monthly payment 10 days ago, payment canceled. We changed funding source to CREDIT_CARD: 
        there is time for nearest payment (we ignore canceled payment, it will be processed by "pay overdue")
    """
    def test_have_time_for_regular_payment_processing__monthly_execution_date_in_past_with_failed_payment(self):
        schedule = self._get_test_schedule_model()
        schedule.start_date = arrow.utcnow().shift(days=-10).datetime.date()
        schedule.period = SchedulePeriod.monthly
        schedule.funding_source_type = FundingSourceType.CREDIT_CARD
        schedule.save()

        self._get_test_schedulepayment_model(schedule, PaymentStatusType.CANCELED).save()

        self.assertTrue(schedule.have_time_for_regular_payment_processing_by_scheduler)


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
            id=uuid4(),
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


class DepositsScheduleModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('test_user')
        UserAccount(account_type=AccountType.personal, user=cls.user).save()

    def test_scheduled_date_without_funding_source_delay(self):
        deposit_payment_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=arrow.utcnow().datetime.date(),
                            origin_user_id=DepositsScheduleModelTest.user.id,
                            deposit_amount=100, deposit_payment_date=deposit_payment_date.datetime.date(),
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.WALLET)
        schedule.save()

        deposit_schedule = DepositsSchedule.objects.get(pk=schedule.id)
        self.assertEqual(deposit_payment_date.datetime.date(), deposit_schedule.scheduled_date)

    def test_scheduled_date_with_credit_card_funding_source_delay(self):
        deposit_payment_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=arrow.utcnow().datetime.date(),
                            origin_user_id=DepositsScheduleModelTest.user.id,
                            deposit_amount=100, deposit_payment_date=deposit_payment_date.datetime.date(),
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.CREDIT_CARD)
        schedule.save()

        deposit_schedule = DepositsSchedule.objects.get(pk=schedule.id)
        self.assertEqual(deposit_payment_date.shift(days=-7).datetime.date(), deposit_schedule.scheduled_date)

    def test_scheduled_date_with_direct_debit_funding_source_delay(self):
        deposit_payment_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=arrow.utcnow().datetime.date(),
                            origin_user_id=DepositsScheduleModelTest.user.id,
                            deposit_amount=100, deposit_payment_date=deposit_payment_date.datetime.date(),
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.DIRECT_DEBIT)
        schedule.save()

        deposit_schedule = DepositsSchedule.objects.get(pk=schedule.id)
        self.assertEqual(deposit_payment_date.shift(days=-7).datetime.date(), deposit_schedule.scheduled_date)


class OnetimeScheduleModelTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('test_user')
        UserAccount(account_type=AccountType.personal, user=cls.user).save()

    def test_scheduled_date_without_funding_source_delay(self):
        start_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=start_date.datetime.date(),
                            origin_user_id=OnetimeScheduleModelTest.user.id,
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.WALLET)
        schedule.save()

        onetime_schedule = OnetimeSchedule.objects.get(pk=schedule.id)
        self.assertEqual(start_date.datetime.date(), onetime_schedule.scheduled_date)

    def test_scheduled_date_with_credit_card_funding_source_delay(self):
        start_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=start_date.datetime.date(),
                            origin_user_id=OnetimeScheduleModelTest.user.id,
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.CREDIT_CARD)
        schedule.save()

        onetime_schedule = OnetimeSchedule.objects.get(pk=schedule.id)
        self.assertEqual(start_date.shift(days=-7).datetime.date(), onetime_schedule.scheduled_date)

    def test_scheduled_date_with_direct_debit_funding_source_delay(self):
        start_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.one_time, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=start_date.datetime.date(),
                            origin_user_id=OnetimeScheduleModelTest.user.id,
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.DIRECT_DEBIT)
        schedule.save()

        onetime_schedule = OnetimeSchedule.objects.get(pk=schedule.id)
        self.assertEqual(start_date.shift(days=-7).datetime.date(), onetime_schedule.scheduled_date)


class WeeklyScheduleModelTest(TestCase):


    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user('test_user')
        UserAccount(account_type=AccountType.personal, user=cls.user).save()

    def test_scheduled_date_without_funding_source_delay(self):
        start_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.weekly, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=start_date.datetime.date(),
                            origin_user_id=WeeklyScheduleModelTest.user.id, number_of_payments=1,
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.WALLET)
        schedule.save()

        weekly_schedule = WeeklySchedule.objects.filter(id=schedule.id)[0]
        self.assertEqual(start_date.datetime.date(), weekly_schedule.scheduled_date)
        #  Not sure why weekly_schedule.scheduled_date has "date" type here, not datetime

    def test_scheduled_date_with_credit_card_funding_source_delay(self):
        start_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.weekly, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=start_date.datetime.date(),
                            origin_user_id=WeeklyScheduleModelTest.user.id, number_of_payments=1,
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.CREDIT_CARD)
        schedule.save()

        weekly_schedule = WeeklySchedule.objects.filter(id=schedule.id)[0]
        self.assertEqual(start_date.shift(days=-7).datetime.date(), weekly_schedule.scheduled_date)
        #  Not sure why weekly_schedule.scheduled_date has "date" type here, not datetime

    def test_scheduled_date_with_direct_debit_funding_source_delay(self):
        start_date = arrow.get(2019, 9, 1)
        schedule = Schedule(period=SchedulePeriod.weekly, status=ScheduleStatus.open, payment_amount=100,
                            purpose=SchedulePurpose.pay, currency=Currency.GBP, payee_id=str(uuid4()),
                            payee_type=PayeeType.WALLET, start_date=start_date.datetime.date(),
                            origin_user_id=WeeklyScheduleModelTest.user.id, number_of_payments=1,
                            funding_source_id=str(uuid4()), funding_source_type=FundingSourceType.DIRECT_DEBIT)
        schedule.save()

        weekly_schedule = WeeklySchedule.objects.filter(id=schedule.id)[0]
        self.assertEqual(start_date.shift(days=-7).datetime.date(), weekly_schedule.scheduled_date)
        #  Not sure why weekly_schedule.scheduled_date has "date" type here, not datetime
