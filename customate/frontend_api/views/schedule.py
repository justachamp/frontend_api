from django.utils.functional import cached_property
from core import views
from django.db.utils import IntegrityError
from rest_framework.permissions import AllowAny
from rest_framework.serializers import ValidationError
from frontend_api.core.client import PaymentApiClient
from frontend_api.fields import ScheduleStatus
from frontend_api.models import Schedule


from ..serializers.schedule import ScheduleSerializer

import logging

logger = logging.getLogger(__name__)


class ScheduleViewSet(views.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = (AllowAny,)

    # Example: /api/v1/schedules/?page[number]=1&filter[currency.iexact]=EUR&filter[name.icontains]=test&sort=-status
    ordering_fields = ('name', 'status')
    search_fields = ('name', )

    filterset_fields = {
        # "exact" filter is excluded by framework, we can use alternative like "filter[currency.iexact]=GBP"
        'name': ('icontains', 'contains', 'iexact'),
        'currency': ('iexact', 'in'),
    }

    def get_queryset(self, *args, **kwargs):
        return Schedule.objects.all().filter(user=self.request.user)

    @cached_property
    def payment_client(self):
        return PaymentApiClient(self.request.user)

    def perform_create(self, serializer):
        try:
            payee_details = self._get_payee_details(serializer.validated_data['payee_id'])
            schedule = serializer.save(user=self.request.user, **payee_details)
            self.calculate_and_set_total_sum_to_pay(schedule)
        except IntegrityError as e:
            #TODO: make sure we handle database integrity errors as validation errors as well
            raise ValidationError(str(e))

    def calculate_and_set_total_sum_to_pay(self, schedule):
        schedule.calculate_and_set_total_sum_to_pay()
        schedule.save(update_fields=["total_sum_to_pay"])

    # We don't remove schedule instance, just changing status (can we change it here?) and cancelling related payments
    def perform_destroy(self, schedule):
        self._cancel_schedule(schedule)

    def _cancel_schedule(self, schedule):
        if not schedule.is_cancelable():
            raise ValidationError({"status": "Schedule with current status cannot be canceled"})
        self._perform_cancellation(schedule)

    def _perform_cancellation(self, schedule):
        schedule.status = ScheduleStatus.canceled
        schedule.save(update_fields=["status"])

        self.payment_client.cancel_schedule_payments(schedule.id)

    def _get_payee_details(self, payee_id):
        payee = self.payment_client.get_payee_details(payee_id)
        if payee is None:
            raise ValidationError({"payee_id": "Payee with such id does not exist"})

        details = {
            'payee_recipient_name': '',
            'payee_recipient_email': '',
            'payee_iban': ''
        }

        try:
            details['payee_recipient_name'] = payee['data']['recipient']['fullName']
            details['payee_recipient_email'] = payee['data']['recipient']['email']
            details['payee_iban'] = payee['data']['account']['iban']
        except KeyError:
            logger.warning('Key error occured during payee processing')

        return details



