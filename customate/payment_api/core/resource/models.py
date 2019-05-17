from functools import reduce
from operator import add
from jsonapi_client import Modifier, Inclusion
from collections import Iterable
import logging

from jsonapi_client.exceptions import DocumentError
from rest_framework.exceptions import ValidationError
from inflection import camelize

from payment_api.core.resource.filters import RQLFilterMixin
from payment_api.core.resource.mixins import JsonApiErrorParser

logger = logging.getLogger(__name__)


class EmptyResponseMeta:

    def __init__(self):
        self.page = {'totalRecords': 0}


class EmptyResponse:

    def __init__(self):
        self.resources = []
        self.meta = EmptyResponseMeta()


class DummyResourceModel:

    def __init__(self, name):
        self._resource = name

    def __getattr__(self, item):
        return self

    @property
    def name(self):
        return self._resource


class ExternalResourceModel:
    _resources = None
    resource_name = None
    external_resource_name = None

    def __init__(self):
        self._resources = []

    def __getattr__(self, item):
        try:
            self._resources.index(item)
            return DummyResourceModel(item)
        except ValueError:
            return self

    @property
    def resource(self):
        return self.external_resource_name or self.resource_name

    @property
    def resources(self):
        return self._resources

    @resources.setter
    def resources(self, resources):
        self._resources = resources


class ResourceQueryset(JsonApiErrorParser, RQLFilterMixin):
    _response = None
    _modifiers = None
    _inclusions = None
    _filters = None
    _pk = None

    def __init__(self, resource, client, method, modifiers=None, inclusions=None, filters=None):
        self.resource = resource
        self.client = client
        self.method = method

        if modifiers:
            self.modifier = modifiers

        if inclusions:
            self.inclusion = inclusions

        if filters:
            self.filter = filters

    def __getitem__(self, item):
        return list(self.iterator())

    @property
    def response(self):
        if not self._response:
            try:
                self._response = self.request(self.resource, self.payload)
            except DocumentError as ex:
                data = self._parse_document_error(ex)
                if data:
                    raise ValidationError(data)
                else:
                    raise ex

        return self._response

    @property
    def payload(self):
        modifiers = self.collected_modifiers
        if self._pk and modifiers:
            return self._pk, modifiers
        else:
            return self._pk if self._pk else modifiers

    @property
    def collected_modifiers(self):
        data = None

        def collect_modifiers(modifier):
            nonlocal data
            if modifier:
                data = data + modifier if data else modifier

        collect_modifiers(self.modifier)
        collect_modifiers(self.inclusion)
        collect_modifiers(self.filter)

        return data

    @property
    def request(self):
        return getattr(self.client, self.method)

    @property
    def modifier(self):
        return self._modifiers

    @modifier.setter
    def modifier(self, modifier):
        if isinstance(modifier, Iterable) and not isinstance(modifier, (str, bytes)):
            modifiers = reduce(add, (Modifier(current_modifier) for current_modifier in modifier))
        else:
            modifiers = Modifier(modifier)

        self._modifiers = self._modifiers + modifiers if self._modifiers else modifiers

    @property
    def filter(self):
        return self._filters

    @filter.setter
    def filter(self, filters):

        def get_modifier(filter_data):
            if isinstance(filter_data, tuple):
                key, value = filter_data
                return Modifier(f'filter{key}{";".join(value) if isinstance(value, list) else value}')
            else:
                return Modifier(filter_data)

        if isinstance(filters, dict):
            filters = reduce(add, (get_modifier(current_filter) for current_filter in filters.items()))
        elif isinstance(filters, Iterable) and not isinstance(filters, (str, bytes)):
            filters = reduce(add, (get_modifier(current_filter) for current_filter in filters))
        else:
            filters = Modifier(filters)

        self._filters = self._filters + filters if self._filters else filters

    def apply_filter(self, filter_data):
        key = next(iter(filter_data))
        self.filter = self.parse_filter(key, filter_data[key])

    @property
    def inclusion(self):
        return self._inclusions

    @inclusion.setter
    def inclusion(self, inclusion):
        if isinstance(inclusion, Iterable) and not isinstance(inclusion, (str, bytes)):
            inclusions = reduce(add, (Inclusion(current_inclusion) for current_inclusion in inclusion))
        else:
            inclusions = Inclusion(inclusion)

        self._inclusions = self._inclusions + inclusions if self._inclusions else inclusions

    def including(self, *args, **kwargs):

        including = ','.join([camelize(part, False) for part in args])
        if len(including):
            self.inclusion = including

        return self

    def order_by(self, *args, **kwargs):

        sort = ','.join(args)
        if len(sort):
            self.modifier = f'sort={sort}'

        return self

    def one(self, pk, map_attributes=True):
        self._pk = pk
        resource = self.response.resource
        resource = self.client.apply_mapping(resource) if map_attributes else resource
        # resource.mark_clean()
        return resource

    def count(self):
        response = self.response
        page = getattr(self.response.meta, 'page', None)
        return page.get('totalRecords') if page else len(response.resources)

    def iterator(self):
        resources = self.response.resources
        return (self.client.apply_mapping(resource) for resource in resources)

    def set_empty_response(self):
        self._response = EmptyResponse()
