from django.utils.functional import cached_property
from django.conf import settings

from payment_api.core.client import Client
from rest_framework_json_api.views import ModelViewSet
from payment_api.core.resource.models import ResourceQueryset



class ResourceViewSet(ModelViewSet):
    resource_name = None
    base_url = settings.PAYMENT_API_URL

    @cached_property
    def client(self):
        embedded_resources = getattr(self.Meta, 'embedded_resources', None) if hasattr(self, 'Meta') else None
        client = Client(self.base_url, embedded_resources=embedded_resources)
        client.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        return client

    @cached_property
    def external_resource_name(self):
        if hasattr(self, 'Meta') and hasattr(self.Meta, 'external_resource_name') and \
                self.Meta.external_resource_name:
            external_resource_name = self.Meta.external_resource_name
        else:
            external_resource_name = self.resource_name

        if external_resource_name != self.resource_name:
            self.client.resource_mapping = {
                'type': {'op': 'edit', 'value': self.resource_name, 'old_value': external_resource_name}
            }

        return external_resource_name

    def get_object(self, map_attributes=True, apply_filters=True):

        # Perform the lookup filtering.
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        # TODO implement get_object_or_404(queryset, **filter_kwargs)
        queryset = ResourceQueryset(self.external_resource_name, self.client, 'get')

        if apply_filters:
            for backend in list(self.filter_backends):
                queryset = backend().filter_queryset(self.request, queryset, self)

        resource = queryset.one(self.kwargs[lookup_url_kwarg], map_attributes=map_attributes)
        self.check_object_permissions(self.request, resource)
        return resource

    def filter_queryset(self, queryset):
        """
        Given a queryset, filter it with whichever filter backend is in use.

        You are unlikely to want to override this method, although you may need
        to call it either from a list view, or from a custom `get_object`
        method if you want to apply the configured filtering backend to the
        default queryset.
        """
        for backend in list(self.filter_backends):
            queryset = backend().filter_queryset(self.request, queryset, self)
        return queryset

    def get_queryset(self):
        page_number = self.request.query_params.get(self.paginator.page_query_param, 1)
        pagination = f'page%5Bnumber%5D={page_number}&page%5Bsize%5D={self.paginator.page_size}&page%5Btotals%5D'
        return ResourceQueryset(self.external_resource_name, self.client, 'get', modifiers=[pagination])

    # def perform_create(self, serializer):
    #     pass
    #
    # def perform_update(self, serializer):
    #     serializer.save()
    #
    # def perform_destroy(self, instance):
    #     pass

