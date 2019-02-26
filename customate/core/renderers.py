"""
Renderers
"""
import copy
from collections import Iterable, OrderedDict, defaultdict

import inflection
from django.db.models import Manager
from django.utils import encoding, six
from rest_framework import relations, renderers
from rest_framework.serializers import BaseSerializer, ListSerializer, Serializer
from rest_framework.settings import api_settings

import rest_framework_json_api
from rest_framework_json_api import utils
from rest_framework_json_api.renderers import JSONRenderer
from rest_framework_json_api.relations import HyperlinkedMixin, ResourceRelatedField, SkipDataMixin


class JSONRenderer(JSONRenderer):


    @classmethod
    def extract_attributes(cls, fields, resource):
        """
        Builds the `attributes` object of the JSON API resource object.
        """
        data = OrderedDict()
        for field_name, field in six.iteritems(fields):
            # ID is always provided in the root of JSON API so remove it from attributes
            if field_name == 'id':
                continue
            # don't output a key for write only fields
            if fields[field_name].write_only:
                continue
            # Skip fields with relations
            if isinstance(
                    field, (relations.RelatedField, relations.ManyRelatedField)
            ):
                continue

            # Skip read_only attribute fields when `resource` is an empty
            # serializer. Prevents the "Raw Data" form of the browsable API
            # from rendering `"foo": null` for read only fields
            try:
                resource[field_name]
            except KeyError:
                if fields[field_name].read_only:
                    continue

            data.update({
                field_name: resource.get(field_name)
            })

        return utils._format_object(data)
