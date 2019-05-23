from django.utils.functional import cached_property
from django.utils.module_loading import import_string as import_class_from_dotted_path
from rest_framework.fields import UUIDField, IntegerField, FloatField, JSONField
from rest_framework.relations import ManyRelatedField
from rest_framework.serializers import raise_errors_on_nested_writes
from rest_framework_json_api.serializers import Serializer, IncludedResourcesValidationMixin
from inflection import camelize

from core.fields import SerializerField
from payment_api.core.resource.models import ExternalResourceModel
from payment_api.core.resource.fields import ExternalResourceRelatedField, ManyRelatedField


class ResourceMeta:
    model = ExternalResourceModel()


class ResourceSerializer(IncludedResourcesValidationMixin, Serializer):
    resource_name = None
    external_resource_name = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.copy_resource_to_meta()
        self.copy_fields_to_meta()
        self._check_resource_mapping()

    def _check_resource_mapping(self):
        if hasattr(self, 'Meta') and hasattr(self.Meta, 'resource_mapping') and self.client:
            self.client.resource_mapping = self.Meta.resource_mapping

    @cached_property
    def service(self):
        if hasattr(self.Meta, 'service'):
            service = import_class_from_dotted_path(self.Meta.service)
            return service(resource=self, context=self.context)
        return None

    @property
    def view(self):
        return self.context.get('view')

    @property
    def request(self):
        return self.context.get('request')

    @property
    def client(self):
        view = self.view
        if view and hasattr(view, 'client'):
            return view.client
        else:
            return self.context.get('client')

    def get_field_name(self, field):
        if isinstance(field, (ExternalResourceRelatedField, ManyRelatedField)):
            if hasattr(field, 'result_source'):
                return field.source
            return camelize(field.field_name, False)
        return field.field_name

    def copy_resource_to_meta(self):
        # @TODO It copies wrong(parent) resource from view for included/related serializers
        view = self.view
        external_resource = None
        resource = None
        if view:
            external_resource = getattr(view.Meta, 'external_resource_name', None) if hasattr(view, 'Meta') else None
            resource = getattr(view, 'resource_name', None)

        external_resource = getattr(self.Meta, 'external_resource_name', external_resource)
        resource = getattr(self.Meta, 'resource_name', resource)

        self.Meta.model.resource_name = resource
        self.Meta.model.external_resource_name = external_resource if external_resource else resource

        if external_resource is not None and external_resource != resource:
            self.client.resource_mapping = {
                'type': {'op': 'edit', 'value': resource, 'old_value': external_resource}
            }

    def copy_fields_to_meta(self):
        resourses = []
        for field in self.fields:
            if isinstance(field, ExternalResourceRelatedField):
                resourses.append(field.source)

        if len(resourses):
            self.Meta.model.resources = resourses

    def create(self, validated_data):
        raise_errors_on_nested_writes('create', self, validated_data)

        self.client.reverse_mapping(validated_data)

        self.client.add_model_schema(self.Meta.model.resource, self.resource_properties)
        instance = self.client.create(self.Meta.model.resource, validated_data)
        return self.client.apply_mapping(instance)

    @cached_property
    def related_resources(self):
        related_resources = getattr(self, 'related_serializers', dict())
        included_resources = getattr(self, 'included_serializers', dict())
        resources = {**related_resources, **included_resources}
        serializers = {}
        for name, value in resources.items():
            if not isinstance(value, type):
                if value == 'self':
                    serializers[name] = self
                else:
                    serializers[name] = import_class_from_dotted_path(value)

        return serializers

    def _related_resource(self, name, field):
        related_resource = field.source
        if name in self.related_resources:
            serializer_class = self.related_resources[name]
            meta = serializer_class.Meta
            related_resource = getattr(meta, 'external_resource_name', getattr(meta, 'resource_name', related_resource))
        return related_resource

    @cached_property
    def resource_properties(self):
        properties = {}

        for name, field in self.fields.items():
            field_source = getattr(field, 'result_source', getattr(field, 'source'))
            if getattr(field, 'read_only', None) and not isinstance(field, (ManyRelatedField, ExternalResourceRelatedField)):
                continue
            elif isinstance(field, ManyRelatedField):
                properties[field_source] = {'relation': 'to-many', 'resource': [self._related_resource(name, field)]}
            elif isinstance(field, ExternalResourceRelatedField):
                properties[field_source] = {'relation': 'to-one', 'resource': [self._related_resource(name, field)]}
            elif isinstance(field, SerializerField):
                properties[field_source] = {'type': ['null', 'array' if field.many else 'object']}
                properties[field_source] = {
                    'relation': 'to-many' if field.many else 'to-one', 'resource': [self._related_resource(name, field)]
                }
            elif isinstance(field, UUIDField):
                properties[field_source] = {'type': ['null', 'string']}
            elif isinstance(field, (IntegerField, FloatField)):
                properties[field_source] = {'type': ['null', 'number']}
            elif isinstance(field, JSONField):
                properties[field_source] = {'type': 'object', 'properties': {}}
            else:
                properties[field_source] = {'type': ['null', 'string']}

        # for name, field in getattr(self, 'included_serializers', {}).items():
        #     properties[name] = {'relation': 'to-one', 'resource': [name]}

        return properties

    def update(self, instance, validated_data):
        raise_errors_on_nested_writes('update', self, validated_data)
        # TODO check type mapping and remove
        instance.type = self.Meta.model.resource
        self.client.reverse_mapping(instance)
        instance = self.client.update(instance, validated_data)
        # refresh cached property
        try:
            del instance.relationships
        except Exception as ex:
            pass
        return self.client.apply_mapping(instance)

    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        if self.client:
            self.client.apply_mapping(instance)
        return super().to_representation(instance)

    class Meta(ResourceMeta):
        pass





