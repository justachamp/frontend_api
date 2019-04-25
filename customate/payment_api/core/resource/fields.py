from rest_framework.relations import ManyRelatedField as DRFManyRelatedField, MANY_RELATION_KWARGS, get_attribute
from payment_api.core.resource.mixins import ResourceMappingMixin
from core.fields import ResourceRelatedField, ResultResourceFieldMixin


def get_pk_from_identifier(resource):
    if not hasattr(resource, 'id') and hasattr(resource, '_resource_identifier'):
        if resource._resource_identifier is not None:
            resource.pk = resource._resource_identifier.id


class ManyRelatedField(DRFManyRelatedField):

    def get_attribute(self, instance):
        # Can't have any relationships if not created
        if hasattr(instance, 'pk') and instance.pk is None:
            return []
        if isinstance(self.source_attrs, list) and hasattr(instance, '_relationships') and instance._relationships:
            if len(self.source_attrs) == 1 and self.source_attrs[0] in instance._relationships:
                relation = instance._relationships.get(self.source_attrs[0])
                resources = None
                if relation:
                    resources = getattr(relation, '_resources', None)
                    identifiers = getattr(relation, '_resource_identifiers', None)
                    resources = resources.values() if resources else identifiers
                return resources
            else:
                return super().get_attribute(instance)
        else:
            return None


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
        if hasattr(value, 'id') or (hasattr(value, '_resource_identifier') and
                                    value._resource_identifier is not None):
            self.apply_mapping(value)
            return super().to_representation(value)
        else:
            return None

    def get_attribute(self, instance):
        # Can't have any relationships if not created
        if not hasattr(instance, 'pk') or (hasattr(instance, 'pk') and instance.pk is None):
            return []
        elif isinstance(self.source_attrs, list) and\
                len(self.source_attrs) == 1 and self._hasattr(instance, self.source_attrs[0]):
            return self._getattr(instance, self.source_attrs[0])

        return super().get_attribute(instance)

    @classmethod
    def many_init(cls, *args, **kwargs):
        """
        This method handles creating a parent `ManyRelatedField` instance
        when the `many=True` keyword argument is passed.

        Typically you won't need to override this method.

        Note that we're over-cautious in passing most arguments to both parent
        and child classes in order to try to cover the general case. If you're
        overriding this method you'll probably want something much simpler, eg:

        @classmethod
        def many_init(cls, *args, **kwargs):
            kwargs['child'] = cls()
            return CustomManyRelatedField(*args, **kwargs)
        """
        list_kwargs = {'child_relation': cls(*args, **kwargs)}
        for key in kwargs:
            if key in MANY_RELATION_KWARGS:
                list_kwargs[key] = kwargs[key]
        return ManyRelatedField(**list_kwargs)
