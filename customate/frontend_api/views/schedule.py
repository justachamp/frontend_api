from core import views
from django.db.utils import IntegrityError
from rest_framework.permissions import AllowAny
from rest_framework.serializers import ValidationError
from frontend_api.models import Schedule
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

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
        except IntegrityError as e:
            #TODO: make sure we handle database integrity errors as validation errors as well
            raise ValidationError(str(e))


    def get_queryset(self, *args, **kwargs):
        return Schedule.objects.all().filter(user=self.request.user)

    # We don't remove schedule instance, just changing status (can we change it here?) and cancelling related payments
    def perform_destroy(self, schedule: Schedule):
        if schedule.status not in [ScheduleStatus.open, ScheduleStatus.overdue]:
            raise ValidationError('Schedule cannot be cancelled')
        schedule.status = ScheduleStatus.cancelled
        schedule.save(update_fields=["status"])
        api_client = PaymentApiClient(schedule.user)
        api_client.cancel_schedule_payments(schedule.id)

