from django.utils.functional import cached_property
from rest_framework_json_api.serializers import (
    ModelSerializer,
    Serializer,
    PKOnlyObject,
    get_resource_type_from_serializer,
    get_included_resources)
from payment_api.core.resource.mixins import ResourceMappingMixin
from payment_api.core.resource.models import ExternalResourceModel, ResourceQueryset
from payment_api.core.resource.fields import ExternalResourceRelatedField
from rest_framework.serializers import raise_errors_on_nested_writes
from collections import OrderedDict

# Non-field imports, but public API
from rest_framework.fields import SkipField




class ResourceMeta:
    model = ExternalResourceModel()


class ResourceSerializer(ResourceMappingMixin, Serializer):
    resource_name = None
    external_resource_name = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.copy_resource_to_meta()
        self.copy_fields_to_meta()
        self.copy_resource_mapping()

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
        view = self.view
        if view:
            external_resource = view.Meta.external_resource_name if hasattr(view, 'Meta') else None
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

    def copy_resource_mapping(self):
        client = self.client
        if client:
            self.resource_mapping = client.resource_mapping

    def create(self, validated_data):
        raise_errors_on_nested_writes('create', self, validated_data)
        self.client.add_model_schema()

        self.client.add_model_schema(self.external_resource_name, self.resource_properties)
        instance = self.client.create(self.Meta.model.resource, validated_data)
        return self.apply_mapping(instance)

    @cached_property
    def resource_properties(self):
        properties = {}

        for field in self.fields:
            properties[field.source] = 'string'

        return properties


    def update(self, instance, validated_data):
        raise_errors_on_nested_writes('update', self, validated_data)
        instance.type = self.Meta.model.resource
        self.unapply_mapping(instance)
        instance = self.client.update(instance, validated_data)
        return self.apply_mapping(instance)

    # def to_representation(self, instance):
    #     """
    #     Object instance -> Dict of primitive datatypes.
    #     """
    #     ret = OrderedDict()
    #     fields = self._readable_fields
    #
    #     for field in fields:
    #         try:
    #             attribute = field.get_attribute(instance)
    #         except SkipField:
    #             continue
    #         except Exception:
    #             continue
    #
    #         # We skip `to_representation` for `None` values so that fields do
    #         # not have to explicitly deal with that case.
    #         #
    #         # For related fields with `use_pk_only_optimization` we need to
    #         # resolve the pk value.
    #
    #         ret[field.field_name] = field.to_representation(attribute)
    #
    #     return ret


    def to_representation(self, instance):
        """
        Object instance -> Dict of primitive datatypes.
        """
        return super().to_representation(instance)
        # ret = OrderedDict()
        # readable_fields = [
        #     field for field in self.fields.values()
        #     if not field.write_only
        # ]
        #
        # for field in readable_fields:
        #     try:
        #         field_representation = self._get_field_representation(field, instance)
        #         ret[field.field_name] = field_representation
        #     except SkipField:
        #         continue
        #
        # return ret

    # def _get_field_representation(self, field, instance):
    #     request = self.context.get('request')
    #     is_included = field.source in get_included_resources(request)
    #     if not is_included and \
    #             isinstance(field, ModelSerializer) and \
    #             hasattr(instance, field.source + '_id'):
    #         attribute = getattr(instance, field.source + '_id')
    #
    #         if attribute is None:
    #             return None
    #
    #         resource_type = get_resource_type_from_serializer(field)
    #         if resource_type:
    #             return OrderedDict([('type', resource_type), ('id', attribute)])
    #
    #     if not hasattr(instance, field.source):
    #         return None
    #
    #     attribute = field.get_attribute(instance)
    #
    #     # We skip `to_representation` for `None` values so that fields do
    #     # not have to explicitly deal with that case.
    #     #
    #     # For related fields with `use_pk_only_optimization` we need to
    #     # resolve the pk value.
    #     check_for_none = attribute.pk if isinstance(attribute, PKOnlyObject) else attribute
    #     if check_for_none is None:
    #         return None
    #     else:
    #         return field.to_representation(attribute)





