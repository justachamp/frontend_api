from functools import reduce
from operator import add
from jsonapi_client import Modifier, Inclusion
from collections import Iterable
import logging

from jsonapi_client.exceptions import DocumentError
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)


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


class ResourceQueryset:

    _response = None
    _modifiers = None
    _inclusions = None
    _pk = None

    def __init__(self, resource, client, method, modifiers=None, inclusions=None):
        self.resource = resource
        self.client = client
        self.method = method

        if modifiers:
            self.modifier = modifiers

        if inclusions:
            self.inclusion = inclusions

    def __getitem__(self, item):
        return list(self.iterator())

    def _parse_document_error(self, ex):
        try:
            resp = ex.response.json()
            errors = resp.get('errors')
            # return {'credentials': ['wrong credentials']}
            data = {}
            for error in errors:
                pointer = error.get('source', {}).get('pointer', '').split('/')[-1]
                if not data.get(pointer):
                    data[pointer] = []
                data[pointer].append(error.get('detail', ''))

            return data if len(data) else None
        except Exception:
            return None


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

        including = ','.join(args)
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
        return self.client.apply_mapping(resource) if map_attributes else resource

    def count(self):
        return self.response.meta.page.get('totalRecords')

    def iterator(self):
        resources = self.response.resources
        return (self.client.apply_mapping(resource) for resource in resources)
