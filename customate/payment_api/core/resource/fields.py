from payment_api.core.resource.mixins import ResourceMappingMixin
from core.fields import ResourceRelatedField, ResultResourceFieldMixin

def get_pk_from_identifier(resource):
    if not hasattr(resource, 'id') and hasattr(resource, '_resource_identifier'):
        resource.pk = resource._resource_identifier.id



class ExternalResourceRelatedField(ResultResourceFieldMixin, ResourceMappingMixin, ResourceRelatedField):

    def __init__(self, *args, **kwargs):
        self.resource_mapping = {'id': {'op': 'copy', 'value': 'pk'}}
        self.resource_mapping = {'id': {'op': 'custom', 'value': get_pk_from_identifier}}
        return super().__init__(*args, **kwargs)

    def get_queryset(self):
        return self

    @property
    def model(self):
        return self

    def get(self, pk):
        return pk

    def __name__(self):
        return None

    def to_representation(self, value):
        self.apply_mapping(value)
        return super().to_representation(value)

    def get_attribute(self, instance):
        # Can't have any relationships if not created
        if not hasattr(instance, 'pk') or (hasattr(instance, 'pk') and instance.pk is None):
            return []

        return super().get_attribute(instance)
