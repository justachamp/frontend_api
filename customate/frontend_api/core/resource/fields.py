from django.utils.functional import cached_property
from django.conf import settings
from rest_framework_json_api import utils

from payment_api.core.resource.fields import ExternalResourceRelatedField as ERRField
from payment_api.core.client import Client
from payment_api.core.resource.models import ResourceQueryset


class ExternalResourceRelatedField(ERRField):
    base_url = settings.PAYMENT_API_URL

    def __init__(self, resource_identifier=None, *args, **kwargs):
        self._resource_identifier = resource_identifier
        super().__init__(*args, **kwargs)

    @cached_property
    def client(self):
        client = Client(self.base_url)
        client.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        return client

    def get_attribute(self, instance):
        queryset = ResourceQueryset(self.source, self.client, 'get')
        included = self.get_included_resources()
        if len(included):
            queryset.including(*included)
        attr_id = getattr(instance, self.attribute_identity_field, None)
        attr = queryset.one(attr_id, map_attributes=True) if attr_id else None
        setattr(instance, self.field_name, attr)
        self.context['client'] = self.client

        return attr

    @property
    def attribute_identity_field(self):
        return f'{self.field_name}_id'

    def get_included_resources(self):
        included_resources = utils.get_included_resources(self.context.get('request'))
        root_source = f'{self.field_name}.'
        return [source.lstrip(root_source) for source in included_resources if source.startswith(root_source)]
