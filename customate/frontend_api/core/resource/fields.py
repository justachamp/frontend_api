from django.utils.functional import cached_property
from django.conf import settings

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
    #
    # def get_object(self, map_attributes=True, apply_filters=True):
    #
    #     # Perform the lookup filtering.
    #     lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
    #     # TODO implement get_object_or_404(queryset, **filter_kwargs)
    #     queryset = ResourceQueryset(self.source, self.client, 'get')
    #
    #     # if apply_filters:
    #     #     for backend in list(self.filter_backends):
    #     #         queryset = backend().filter_queryset(self.request, queryset, self)
    #
    #     # resource = queryset.one(self.kwargs[lookup_url_kwarg], map_attributes=map_attributes)
    #     resource = queryset.one(instance.payment_account_id, map_attributes=map_attributes)
    #     # self.check_object_permissions(self.request, resource)
    #     return resource


    def get_attribute(self, instance):
        # Perform the lookup filtering.
        # lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        # TODO implement get_object_or_404(queryset, **filter_kwargs)
        queryset = ResourceQueryset(self.source, self.client, 'get')

        # if apply_filters:
        #     for backend in list(self.filter_backends):
        #         queryset = backend().filter_queryset(self.request, queryset, self)

        # resource = queryset.one(self.kwargs[lookup_url_kwarg], map_attributes=map_attributes)
        attr = queryset.one(instance.payment_account_id, map_attributes=True) if instance.payment_account_id else None
        setattr(instance, self.field_name, attr)
        return attr
        # self.check_object_permissions(self.request, resource)
        # return resource
        # queryset = ResourceQueryset(self.external_resource_name, self.client, 'get')
        #
        #
        #
        #
        # return  self.client.super().get_attribute(instance)