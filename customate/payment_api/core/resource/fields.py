from payment_api.core.resource.mixins import ResourceMappingMixin
from core.fields import ResourceRelatedField


class ExternalResourceRelatedField(ResourceMappingMixin, ResourceRelatedField):

    def get_queryset(self):
        return None

    def to_representation(self, value):
        self.apply_mapping(value)
        return super().to_representation(value)

    def get_attribute(self, instance):
        # Can't have any relationships if not created
        if not hasattr(instance, 'pk') or (hasattr(instance, 'pk') and instance.pk is None):
            return []

        return super().get_attribute(instance)
