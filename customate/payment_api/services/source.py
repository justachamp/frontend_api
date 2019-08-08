from jsonapi_client.resourceobject import ResourceObject

from core.fields import PayeeType
from payment_api.services import (
    BaseRequestResourceSerializerService as BaseService,
    RequestResourceQuerysetMixin as QuerysetMixin
)


class FundingSourceRequestResourceService(BaseService, QuerysetMixin):
    def get_source_details(self, source_id) -> ResourceObject:
        return self.queryset.one(source_id)

    class Meta:
        resource_name = 'funding_sources'
