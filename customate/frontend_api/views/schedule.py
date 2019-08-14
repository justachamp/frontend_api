import logging
from traceback import format_exc
from django.utils.functional import cached_property
from rest_framework import status as status_codes
from rest_framework.exceptions import NotFound

from core import views
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError
from frontend_api.tasks import make_overdue_payment
from frontend_api.core.client import PaymentApiClient
from frontend_api.fields import ScheduleStatus
from frontend_api.models import Schedule
from frontend_api.permissions import (
    IsOwnerOrReadOnly,
    IsSuperAdminOrReadOnly,
    SubUserManageSchedulesPermission,
    IsNotBlocked,
    IsActive
)

from frontend_api.serializers.schedule import ScheduleSerializer

logger = logging.getLogger(__name__)


class ScheduleViewSet(views.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
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
        """
        Create new Schedule / HTTP CREATE

        :param serializer:
        :return:
        """
        try:
            pd = self.payment_client.get_payee_details(serializer.validated_data["payee_id"])
            schedule = serializer.save(
                user=self.request.user,
                payee_recipient_name=pd.recipient_name,
                payee_recipient_email=pd.recipient_email,
                payee_iban=pd.iban,
                payee_title=pd.title,
                number_of_payments_left=serializer.validated_data["number_of_payments"]
            )

            # schedule.save()
            logger.info("Successfully created new schedule_id=%r" % schedule.id)
        except Exception as e:
            logger.error("Unable to save Schedule=%r, due to %r" % (serializer.validated_data, format_exc()))
            raise ValidationError("Unable to save schedule")

    def perform_destroy(self, schedule: Schedule):
        """
        Handle HTTP DELETE here.
        We don't remove schedule instance, just changing status and cancelling related payments
        :param schedule:
        :return:
        """

        if not schedule.is_cancelable():
            raise ValidationError({"status": "Schedule with current status cannot be canceled"})

        # cancel Schedule
        schedule.move_to_status(ScheduleStatus.cancelled)
        self.payment_client.cancel_schedule_payments(schedule.id)

    # TODO perform_edit

    def pay_overdue(self, request, *args, **kwargs):
        """
        Tries to initiate the sequence of overdue payments initiated by client.
        :param request:
        :param args:
        :param kwargs:
        :return:
        """
        schedule_id = kwargs.get('pk')

        try:
            schedule = Schedule.objects.get(id=schedule_id)
        except Exception as e:
            raise ValidationError("Unable to fetch schedule_id=%s " % schedule_id)

        schedule.move_to_status(ScheduleStatus.processing)
        make_overdue_payment.delay(
            schedule_id=schedule_id,
            user_id=request.user.id
        )
        return Response(status=status_codes.HTTP_204_NO_CONTENT)