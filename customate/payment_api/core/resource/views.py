from payment_api.core.client import Client
from rest_framework_json_api.views import ModelViewSet
from rest_framework.response import Response
from payment_api.core.resource.models import ResourceQueryset
PAYMENT_API_URL = 'http://local-dev-app.customate.net:8081/'


class ResourceViewSet(ModelViewSet):
    resource_name = None
    base_url = PAYMENT_API_URL
    _external_resource_name = None
    _client = None

    # def get_serializer_context(self):
    #     """
    #     Extra context provided to the serializer class.
    #     """
    #     return {
    #         'request': self.request,
    #         'format': self.format_kwarg,
    #         'view': self
    #     }

    @property
    def client(self):
        if not self._client:
            self._client = Client(self.base_url)
            self._client.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        return self._client

    # def update(self, request, *args, **kwargs):
    #     partial = kwargs.pop('partial', False)
    #     instance = self.get_object(apply_filters=False, map_attributes=False)
    #     serializer = self.get_serializer(instance, data=request.data, partial=partial)
    #     serializer.is_valid(raise_exception=True)
    #     self.perform_update(serializer)
    #
    #     if getattr(instance, '_prefetched_objects_cache', None):
    #         # If 'prefetch_related' has been applied to a queryset, we need to
    #         # forcibly invalidate the prefetch cache on the instance.
    #         instance._prefetched_objects_cache = {}
    #
    #     return Response(serializer.data)

    @property
    def external_resource_name(self):

        if not self._external_resource_name:
            if hasattr(self, 'Meta') and hasattr(self.Meta, 'external_resource_name'):
                self._external_resource_name = self.Meta.external_resource_name
            else:
                self._external_resource_name = self.resource_name

            if self._external_resource_name and self._external_resource_name != self.resource_name:
                self.client.resource_mapping = {
                    'type': {'op': 'edit', 'value': self.resource_name, 'old_value': self._external_resource_name}
                }

        return self._external_resource_name

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

