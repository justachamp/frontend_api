from traceback import format_exc
from django.utils.functional import cached_property
from core import views
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from frontend_api.core.client import PaymentApiClient
from frontend_api.fields import ScheduleStatus
from frontend_api.models import Schedule
from frontend_api.permissions import (
    IsOwnerOrReadOnly,
    IsSuperAdminOrReadOnly,
    SubUserManageSchedulesPermission
)

from ..serializers.schedule import ScheduleSerializer

import logging

logger = logging.getLogger(__name__)


class ScheduleViewSet(views.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = (IsAuthenticated,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManageSchedulesPermission)

    # Example: /api/v1/schedules/?page[number]=1&filter[currency.iexact]=EUR&filter[name.icontains]=test&sort=-status
    ordering_fields = ('name', 'status')
    search_fields = ('name', 'payee_recipient_name', 'payee_recipient_email', 'payee_iban')

    filterset_fields = {
        # "exact" filter is excluded by framework, we can use alternative like "filter[currency.iexact]=GBP"
        'name': ('icontains', 'contains', 'iexact'),
        'payee_title': ('icontains', 'contains', 'iexact'),
        'payee_recipient_name': ('icontains', 'contains', 'iexact'),
        'payee_recipient_email': ('icontains', 'contains', 'iexact'),
        'payee_iban': ('icontains', 'contains', 'iexact'),
        'currency': ('iexact', 'in'),
    }

    def get_queryset(self, *args, **kwargs):
        account = self.request.user.account
        owner_account = account.owner_account if self.request.user.is_subuser else account
        target_account_ids = [owner_account.id] + list(
            owner_account.sub_user_accounts.all().values_list('id', flat=True)
        )
        return Schedule.objects.all().filter(user__account__id__in=target_account_ids)

    @cached_property
    def payment_client(self):
        return PaymentApiClient(self.request.user)

    def perform_create(self, serializer):
        try:
            payee_details = self.get_payee_details(serializer.validated_data["payee_id"])
            schedule = serializer.save(user=self.request.user, **payee_details)
            schedule.calculate_and_set_total_sum_to_pay()
            schedule.save(update_fields=["total_sum_to_pay"])
        except Exception as e:
            logger.error("Unable to save Schedule=%r, due to %r" % (serializer.validated_data, format_exc()))
            raise ValidationError(str(e))

    # We don't remove schedule instance, just changing status (can we change it here?) and cancelling related payments
    def perform_destroy(self, schedule):
        if not schedule.is_cancelable():
            raise ValidationError({"status": "Schedule with current status cannot be canceled"})

        # cancel Schedule
        schedule.status = ScheduleStatus.cancelled
        schedule.save(update_fields=["status"])
        self.payment_client.cancel_schedule_payments(schedule.id)

    def get_payee_details(self, payee_id):
        payee_details = self.payment_client.get_payee_details(payee_id)
        return {
            'payee_recipient_name': payee_details.recipient_name,
            'payee_recipient_email': payee_details.recipient_email,
            'payee_iban': payee_details.iban,
            'payee_title': payee_details.title
        }
