"""
Renderers
"""
import copy
from collections import Iterable, OrderedDict, defaultdict

import inflection
from django.db.models import Manager
from django.utils import encoding, six
from rest_framework import relations, renderers
from rest_framework.relations import ManyRelatedField
from rest_framework.serializers import BaseSerializer, ListSerializer, Serializer
from rest_framework.settings import api_settings

import rest_framework_json_api
from rest_framework_json_api import utils
from rest_framework_json_api.renderers import JSONRenderer
from rest_framework_json_api.relations import HyperlinkedMixin, ResourceRelatedField, SkipDataMixin


class JSONRenderer(JSONRenderer):

    # @classmethod
    # def extract_attributes(cls, fields, resource):
    #     """
    #     Builds the `attributes` object of the JSON API resource object.
    #     """
    #     data = OrderedDict()
    #     for field_name, field in six.iteritems(fields):
    #         # ID is always provided in the root of JSON API so remove it from attributes
    #         if field_name == 'id':
    #             continue
    #         # don't output a key for write only fields
    #         if fields[field_name].write_only:
    #             continue
    #         # Skip fields with relations
    #         if isinstance(
    #                 field, (relations.RelatedField, relations.ManyRelatedField, BaseSerializer)
    #         ):
    #             continue
    #
    #         # Skip read_only attribute fields when `resource` is an empty
    #         # serializer. Prevents the "Raw Data" form of the browsable API
    #         # from rendering `"foo": null` for read only fields
    #         try:
    #             resource[field_name]
    #         except KeyError:
    #             if fields[field_name].read_only:
    #                 continue
    #
    #         data.update({
    #             field_name: resource.get(field_name)
    #         })
    #
    #     return utils._format_object(data)


    @classmethod
    def build_json_resource_obj(cls, fields, resource, resource_instance, resource_name,
                                force_type_resolution=False):
        """
        Builds the resource object (type, id, attributes) and extracts relationships.
        """
        # Determine type from the instance if the underlying model is polymorphic
        if force_type_resolution:
            resource_name = utils.get_resource_type_from_instance(resource_instance)

        pk = resource_instance.pk if hasattr(resource_instance, 'pk') else resource_instance.id
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

    # @classmethod
    # def extract_relationships(cls, fields, resource, resource_instance):
    #     from collections import namedtuple
    #     JSONAPIMeta = namedtuple('JSONAPIMeta', 'resource_name')
    #
    #     for key in fields:
    #         if isinstance(fields[key], ManyRelatedField):
    #             fields[key].JSONAPIMeta = JSONAPIMeta(resource_name='wallets')
    #     return super().extract_relationships(fields, resource, resource_instance)