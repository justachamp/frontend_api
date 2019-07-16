"""
Renderers
"""
import logging
from collections import OrderedDict

from django.utils import encoding
from jsonapi_client.resourceobject import ResourceObject as JSONAPIClientResourceObject
from rest_framework import relations

from rest_framework.settings import api_settings

from rest_framework_json_api import utils
from rest_framework_json_api.renderers import JSONRenderer

logger = logging.getLogger(__name__)


class ExternalResourceWrapper:
    def __init__(self, resource):
        self._resource = resource

    def __getattr__(self, item):
        if self._hasattr(item):
            return self._getattr(item)
        else:
            return getattr(self._resource, item)

    def _hasattr(self, key):
        return key in self._resource._attributes or key in self._resource._relationships

    def _getattr(self, key, def_val=None):

        if key in self._resource._attributes:
            return self._resource._attributes[key]

        elif key in self._resource._relationships:
            return self._resource._relationships[key]

        else:
            return def_val


class CustomateJSONRenderer(JSONRenderer):

    @classmethod
    def build_json_resource_obj(cls, fields, resource, resource_instance, resource_name,
                                force_type_resolution=False):
        """
        Builds the resource object (type, id, attributes) and extracts relationships.
        """
        # Determine type from the instance if the underlying model is polymorphic
        if force_type_resolution:
            resource_name = utils.get_resource_type_from_instance(resource_instance)

        pk = (resource_instance.get("pk") if isinstance(resource_instance, dict) else None) or \
             (resource_instance.pk if hasattr(resource_instance, "pk") else None) or \
             None

        resource_data = [
            ('type', resource_name),
            ('id', encoding.force_text(pk) if resource_instance else None),
            ('attributes', cls.extract_attributes(fields, resource)),
        ]
        relationships = cls.extract_relationships(fields, resource, resource_instance)
        if relationships:
            resource_data.append(('relationships', relationships))
        # Add 'self' link if field is present and valid
        if api_settings.URL_FIELD_NAME in resource and \
                isinstance(fields[api_settings.URL_FIELD_NAME], relations.RelatedField):
            resource_data.append(('links', {'self': resource[api_settings.URL_FIELD_NAME]}))
        return OrderedDict(resource_data)

    @classmethod
    def extract_relation_instance(cls, field_name, field, resource_instance, serializer):
        field_name = serializer.get_field_name(field) if hasattr(serializer, 'get_field_name') else field_name
        return super().extract_relation_instance(field_name, field, resource_instance, serializer)

    @classmethod
    def extract_relationships(cls, fields, resource, resource_instance):
        resource_instance = ExternalResourceWrapper(resource_instance) \
            if isinstance(resource_instance, JSONAPIClientResourceObject) else resource_instance
        return super().extract_relationships(fields, resource, resource_instance)
