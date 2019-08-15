import logging
from django.utils.functional import cached_property
from django.conf import settings

from payment_api.core.client import Client
from rest_framework_json_api.views import ModelViewSet, RelationshipView
from payment_api.core.resource.models import ResourceQueryset

logger = logging.getLogger(__name__)


class ResourceViewSet(ModelViewSet):
    _queryset = None
    resource_name = None
    paginate_response = True
    base_url = settings.PAYMENT_API_URL

    @cached_property
    def client(self):
        embedded_resources = getattr(self.Meta, 'embedded_resources', None) if hasattr(self, 'Meta') else None
        resource_suffix_name = getattr(self.Meta, 'resource_suffix_name', None) if hasattr(self, 'Meta') else None
        client = Client(self.base_url, embedded_resources=embedded_resources, url_suffix=resource_suffix_name)
        client.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        self._check_resource_mapping(client)
        return client

    def _check_resource_mapping(self, client):
        if self._meta and hasattr(self._meta, 'resource_mapping'):
            client.resource_mapping = self._meta.resource_mapping

    @cached_property
    def _meta(self):
        return getattr(self, 'Meta', None)

    @cached_property
    def external_resource_name(self):

        if hasattr(self.serializer_class.Meta, 'external_resource_name') and \
                self.serializer_class.Meta.external_resource_name:
            external_resource_name = self.serializer_class.Meta.external_resource_name

        elif self._meta and hasattr(self._meta, 'external_resource_name') and \
                self._meta.external_resource_name:
            external_resource_name = self.Meta.external_resource_name

        else:
            external_resource_name = getattr(self.serializer_class.Meta, 'resource_name',
                                             getattr(self, 'resource_name', None))
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
        if not self._queryset:
            modifiers = []
            if self.paginate_response:
                page_size = int(self.request.query_params.get(self.paginator.page_size_query_param, self.paginator.page_size))
                if page_size > int(settings.FULL_RESOURCE_LIST_PAGE_SIZE):
                    page_size = settings.FULL_RESOURCE_LIST_PAGE_SIZE
                page_number = self.request.query_params.get(self.paginator.page_query_param, 1)
            else:
                page_size = settings.FULL_RESOURCE_LIST_PAGE_SIZE
                page_number = 1

            pagination = f'page[number]={page_number}&page[size]={page_size}&page[totals]'
            modifiers.append(pagination)
            logger.debug("pagination: %r " % pagination)
            self._queryset = ResourceQueryset(self.external_resource_name, self.client, 'get', modifiers=modifiers)

        return self._queryset

    # def perform_create(self, serializer):
    #     pass
    #
    # def perform_update(self, serializer):
    #     serializer.save()
    #
    def perform_destroy(self, instance):
        instance.delete()
        instance.commit()


class ResourceRelationshipView(RelationshipView):

    def get_queryset(self):
        pass
