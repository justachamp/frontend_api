from django.utils.functional import cached_property
from rest_framework.fields import UUIDField, EmailField, IntegerField
from rest_framework.relations import ManyRelatedField
from rest_framework_json_api.serializers import Serializer
from payment_api.core.resource.models import ExternalResourceModel
from payment_api.core.resource.fields import ExternalResourceRelatedField
from rest_framework.serializers import raise_errors_on_nested_writes


class ResourceMeta:
    model = ExternalResourceModel()


class ResourceSerializer(Serializer):
    resource_name = None
    external_resource_name = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.copy_resource_to_meta()
        self.copy_fields_to_meta()

    @property
    def view(self):
        return self.context.get('view')

    @property
    def rquest(self):
        return self.context.get('request')

    @property
    def client(self):
        view = self.view
        return self.view.client if view else None

    def copy_resource_to_meta(self):
        # @TODO It copies wrong(parent) resource from view for included/related serializers
        view = self.view
        if view:
            external_resource = getattr(view.Meta, 'external_resource_name', None) if hasattr(view, 'Meta') else None
            resource = view.resource_name
            self.Meta.model.resource_name = resource
            self.Meta.model.external_resource_name = external_resource if external_resource else resource

    def copy_fields_to_meta(self):
        resouurses = []
        for field in self.fields:
            if isinstance(field, ExternalResourceRelatedField):
                resouurses.append(field.source)

        if len(resouurses):
            self.Meta.model.resources = resouurses

    def create(self, validated_data):
        raise_errors_on_nested_writes('create', self, validated_data)

        self.client.add_model_schema(self.Meta.model.resource, self.resource_properties)
        instance = self.client.create(self.Meta.model.resource, validated_data)
        return self.client.apply_mapping(instance)

    @cached_property
    def resource_properties(self):
        properties = {}

        for name, field in self.fields.items():
            if isinstance(field, ManyRelatedField):
                properties[field.source] = {'relation': 'to-many', 'resource': [field.source]}
            elif isinstance(field, UUIDField):
                properties[field.source] = {'type': ['null', 'string']}
            elif isinstance(field, IntegerField):
                properties[field.source] = {'type': 'number'}
            else:
                properties[field.source] = {'type': 'string'}

        return properties

    def update(self, instance, validated_data):
        raise_errors_on_nested_writes('update', self, validated_data)
        # TODO check type mapping and remove
        instance.type = self.Meta.model.resource
        self.client.reverse_mapping(instance)
        instance = self.client.update(instance, validated_data)
        return self.client.apply_mapping(instance)

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        return super().to_representation(instance)

    class Meta(ResourceMeta):
        pass





