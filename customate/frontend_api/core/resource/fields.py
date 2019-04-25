from django.utils.functional import cached_property
from django.conf import settings
from rest_framework_json_api import utils

from payment_api.core.resource.fields import ExternalResourceRelatedField
from payment_api.core.client import Client
from payment_api.core.resource.models import ResourceQueryset



class ExternalResourceRelatedField(ExternalResourceRelatedField):
    base_url = settings.PAYMENT_API_URL

    def __init__(self, resource_identifier=None, *args, **kwargs):
        self._resource_identifier = resource_identifier
        return super().__init__(*args, **kwargs)

    @cached_property
    def client(self):
        client = Client(self.base_url)
        client.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        # if self.field_name != self.source:
        #     self.client.resource_mapping = {
        #         'type': {'op': 'edit', 'value': self.field_name, 'old_value': self.source}
        #     }

        return client

    def get_attribute(self, instance):
        queryset = ResourceQueryset(self.source, self.client, 'get')
        included = self.get_included_resources()
        if len(included):
            queryset.including(*included)
        attr = queryset.one(instance.payment_account_id, map_attributes=True) if instance.payment_account_id else None
        setattr(instance, self.field_name, attr)
        self.context['client'] = self.client

        return attr

    def get_included_resources(self):
        included_resources = utils.get_included_resources(self.context.get('request'))
        root_source = f'{self.field_name}.'
        return [source.lstrip(root_source) for source in included_resources if source.startswith(root_source)]
