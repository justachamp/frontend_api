from traceback import format_exc
from typing import List, Tuple, Union

from django.utils.functional import cached_property
from jsonapi_client.resourceobject import ResourceObject
from rest_framework.exceptions import ValidationError
from jsonapi_client import Session as DefaultSession, Modifier
import logging

# Get an instance of a logger
from jsonapi_client.exceptions import DocumentError
from jsonapi_client.common import jsonify_attribute_name, error_from_response, HttpStatus, HttpMethod
import collections

from payment_api.core.resource.mixins import ResourceMappingMixin, JsonApiErrorParser

logger = logging.getLogger(__name__)


class ResourceObjectWithCustomId(ResourceObject):
    def __init__(self, session: 'Session', data: Union[dict, list]) -> None:
        self._force_create = False
        super().__init__(session, data)

    def force_create(self):
        """
        Parent class defines whether resource should be created only by empty "id" field, it's not an option because
        we may want to set custom id for new resource, this kind of scenario is handled with help of "_force_create"
        field
        """
        self._force_create = True

    @property
    def _http_method(self):
        return HttpMethod.PATCH if self.id and not self._force_create else HttpMethod.POST


class Session(DefaultSession):
    def __init__(self, *args, **kwargs) -> None:
        request_kwargs = {'headers': self._generate_request_headers()}
        super().__init__(request_kwargs=request_kwargs, *args, **kwargs)

    def _generate_request_headers(self):
        return {
            'Request-Id': logging.get_shared_extra_param('requestId')
        }

    def _get_sync(self, resource_type: str,
                  resource_id_or_filter: 'Union[Modifier, str]' = None) -> 'Document':
        resource_id, filter_ = self._resource_type_and_filter(resource_id_or_filter)
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

        if isinstance(json_data, dict) and json_data.get('errors'):
            logger.info("Payment API errors: %r" % json_data.get('errors'))

        doc = super().read(json_data, url, no_cache=False)
        return doc

    def _ext_fetch_by_url(self, url: str) -> 'Document':
        logger.info('Fetching Payment API resource: url=%s' % url)
        return super()._ext_fetch_by_url(url)

    def http_request(self, http_method: str, url: str, send_json: dict,
                     expected_statuses: List[str] = None) -> Tuple[int, dict, str]:
        """
        Internal use.
        Method to make PATCH/POST requests to server using requests library.
        """
        self.assert_sync()
        import requests
        expected_statuses = expected_statuses or HttpStatus.ALL_OK

        self._request_kwargs["headers"].update({'Content-Type': 'application/vnd.api+json'})
        logger.info("Request to Payment API: url=%s, method=%s", url, http_method, extra={'body': send_json})
        response = requests.request(http_method, url, json=send_json,
                                    **self._request_kwargs)
        logger.info("Response from Payment API: status=%s", response.status_code, extra={'body': response.text})

        if response.status_code not in expected_statuses:
            raise DocumentError(f'Could not {http_method.upper()} '
                                f'({response.status_code}): '
                                f'{error_from_response(response)}',
                                errors={'status_code': response.status_code},
                                response=response,
                                json_data=send_json)

        return response.status_code, response.json() \
            if response.content \
            else {}, response.headers.get('Location')

    # The only difference from parent's method is that we return ResourceObjectWithCustomId object, that provides
    # possibility to provide custom id to resource
    def create(self, _type: str, fields: dict=None, **more_fields) -> 'ResourceObject':
        """
        Create a new ResourceObject of model _type. This requires that schema is defined
        for model.

        If you have field names that have underscores, you can pass those fields
        in fields dictionary.

        """
        from jsonapi_client.objects import RESOURCE_TYPES

        if fields is None:
            fields = {}

        attrs: dict = {}
        rels: dict = {}
        schema = self.schema.schema_for_model(_type)
        more_fields.update(fields)

        for key, value in more_fields.items():
            if key not in fields:
                key = jsonify_attribute_name(key)
            props = schema['properties'].get(key, {})
            if 'relation' in props:
                res_types = props['resource']
                if isinstance(value, RESOURCE_TYPES + (str,)):
                    value = self._value_to_dict(value, res_types)
                elif isinstance(value, collections.Iterable):
                    value = [self._value_to_dict(id_, res_types) for id_ in value]
                rels[key] = {'data': value}
            else:
                key = key.split('.')
                a = attrs
                for k in key[:-1]:
                    a_ = a[k] = a.get(k, {})
                    a = a_

                a[key[-1]] = value

        data = {'type': _type,
                'id': None,
                'attributes': attrs,
                'relationships': rels,
                }

        res = ResourceObjectWithCustomId(self, data)
        return res


class Client(ResourceMappingMixin, JsonApiErrorParser):
    _base_url = None
    _embedded_resources = None
    _url_suffix = None

    def __init__(self, base_url, embedded_resources=None, url_suffix=None, *args, **kwargs):
        self._base_url = base_url
        self._embedded_resources = embedded_resources
        self._url_suffix = url_suffix
        super().__init__(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self.client, item)

    def get_post_url(self, instance):
        url = instance.post_url
        return f'{url}/{self.url_suffix}' if self.url_suffix else url

    @property
    def embedded_resources(self):
        return self._embedded_resources if isinstance(self._embedded_resources, list) else []

    @property
    def url_suffix(self):
        return self._url_suffix

    @cached_property
    def client(self):
        return Session(self._base_url, schema={})

    @property
    def request_kwargs(self):
        return self.client._request_kwargs

    @request_kwargs.setter
    def request_kwargs(self, request_kwargs):
        self.client._request_kwargs = request_kwargs

    def _apply_resource_id(self, instance, attributes):
        if attributes.get('id') and instance.id is None:
            instance.id = attributes.get('id')
            del(attributes['id'])

    def _apply_resource_attributes(self, instance, attributes):
        relationships = instance._relationships.keys()
        embedded_resources = self.embedded_resources

        for key, value in attributes.items():
            if key in relationships and key in embedded_resources or key in instance._attributes:
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
            instance.commit(custom_url=self.get_post_url(instance))

            return instance

        except DocumentError as ex:
            logger.info("PaymentClient.update caught a document error: %r " % format_exc())
            data = self._parse_document_error(ex)
            if data:
                raise ValidationError(data)
            else:
                raise ex

    def create(self, resource_name, attributes):
        try:
            instance = self.client.create(resource_name)
            self._apply_resource_id(instance, attributes)
            self._apply_resource_attributes(instance, attributes)

            instance.force_create()
            instance.commit(custom_url=self.get_post_url(instance))

            logger.debug(instance)
            return instance
        except DocumentError as ex:
            logger.info("PaymentClient.create caught a document error: %r " % format_exc())
            data = self._parse_document_error(ex)
            if data:
                raise ValidationError(data)
            else:
                try:
                    error = ex.response.json()
                except Exception as ex:
                    error = ex.response.content

                raise ValidationError([error, ex.json_data])

    def delete(self, resource_name, resource_id):
        try:
            instance = self.client.create(resource_name)
            instance.id = resource_id

            # Looks like we have to add resource to the session this way, so that it could be successfully remove by
            # delete operation
            self.client.add_resources(instance)
            instance.delete()
            instance.commit()
        except DocumentError as ex:
            logger.info("PaymentClient.delete caught a document error: %r " % format_exc())
            data = self._parse_document_error(ex)
            if data:
                raise ValidationError(data)
            else:
                raise ex

    def add_model_schema(self, resource_name, properties):
        self.client.schema.add_model_schema({resource_name: {'properties': properties}})
