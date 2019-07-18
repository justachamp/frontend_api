from jsonapi_client.resourceobject import ResourceObject

from payment_api.services import (
    BaseRequestResourceSerializerService as BaseService,
    RequestResourceQuerysetMixin as QuerysetMixin,
)


class ScheduleRequestResourceService(BaseService, QuerysetMixin):
    def get_schedule_payment_details(self, schedule_id) -> ResourceObject:
        return self.queryset.one(schedule_id)

    class Meta:
        resource_name = 'schedule_payments'
