from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from jsonapi_client import Session as DefaultSession, Filter, ResourceTuple, Modifier
import logging

# Get an instance of a logger
from jsonapi_client.exceptions import DocumentError

from payment_api.core.resource.mixins import ResourceMappingMixin, JsonApiErrorParser

logger = logging.getLogger(__name__)


class Session(DefaultSession):
    def _get_sync(self, resource_type: str,
                  resource_id_or_filter: 'Union[Modifier, str]' = None) -> 'Document':
        resource_id, filter_ = self._resource_type_and_filter(
                                                                resource_id_or_filter)
        url = self._url_for_resource(resource_type, resource_id, filter_)
        return self.fetch_document_by_url(url)

    @staticmethod
    def _resource_type_and_filter(
            resource_id_or_filter: 'Union[Modifier, str]' = None) \
            -> 'Tuple[Optional[str], Optional[Modifier]]':

        if isinstance(resource_id_or_filter, tuple):
            resource_id = resource_id_or_filter[0]
            resource_filter = resource_id_or_filter[1]
        elif isinstance(resource_id_or_filter, Modifier):
            resource_id = None
            resource_filter = resource_id_or_filter
        else:
            resource_id = resource_id_or_filter
            resource_filter = None
        return resource_id, resource_filter

    def read(self, json_data: dict, url='', no_cache=False):
        def check_data_format(item):
            if isinstance(item, dict) and not item.get('attributes'):
                item['attributes'] = {}

        if isinstance(json_data, dict) and json_data.get('data'):
            data = json_data.get('data')

            if isinstance(data, list):
                for item in data:
                        check_data_format(item)
            else:
                check_data_format(data)

        doc = super().read(json_data, url, no_cache=False)
        return doc

    def _ext_fetch_by_url(self, url: str) -> 'Document':
        logger.error(f'fetch_by_url: {url}')
        return super()._ext_fetch_by_url(url)


class Client(ResourceMappingMixin, JsonApiErrorParser):

    _base_url = None
    _embedded_resources = None

    def __init__(self, base_url, embedded_resources=None, *args, **kwargs):
        self._base_url = base_url
        self._embedded_resources = embedded_resources
        super().__init__(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self.client, item)

    @property
    def embedded_resources(self):
        return self._embedded_resources if isinstance(self._embedded_resources, list) else []

    @cached_property
    def client(self):
        return Session(self._base_url, schema={})

    @property
    def request_kwargs(self):
        return self.client._request_kwargs

    @request_kwargs.setter
    def request_kwargs(self, request_kwargs):
        self.client._request_kwargs = request_kwargs

    def _apply_resource_attributes(self, instance, attributes):
        relationships = instance._relationships.keys()
        embedded_resources = self.embedded_resources

        for key, value in attributes.items():
            if key in relationships and key in embedded_resources:
                instance._attributes[key] = value
                instance.dirty_fields.add(key)
            elif key in instance._relationships:
                instance._relationships[key].set(value)
            else:
                setattr(instance, key, value)
        return instance

    def update(self, instance, attributes):
        try:
            self._apply_resource_attributes(instance, attributes)
            instance.commit()

            return instance

        except DocumentError as ex:
            data = self._parse_document_error(ex)
            if data:
                raise ValidationError(data)
            else:
                raise ex

    def create(self, resource_name, attributes):
        try:

            instance = self.client.create(resource_name)
            self._apply_resource_attributes(instance, attributes)
            instance.commit()

            logger.error(instance)
            return instance
        except DocumentError as ex:
            data = self._parse_document_error(ex)
            if data:
                raise ValidationError(data)
            else:
                try:
                    error = ex.response.json()
                except Exception as ex:
                    error = ex.response.content

                raise ValidationError([error, ex.json_data])

    def add_model_schema(self, resource_name, properties):
        self.client.schema.add_model_schema({resource_name: {'properties': properties}})


