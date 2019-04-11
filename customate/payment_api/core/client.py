from django.utils.functional import cached_property
from jsonapi_client import Session as DefaultSession, Filter, ResourceTuple, Modifier
import logging

# Get an instance of a logger
from jsonapi_client.exceptions import DocumentError

from payment_api.core.resource.mixins import ResourceMappingMixin

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


class Client(ResourceMappingMixin):

    _base_url = None
    _embeded_attributes = None

    def __init__(self, base_url, embeded_attributes=None, *args, **kwargs):
        self._base_url = base_url
        self._embeded_attributes = embeded_attributes
        super().__init__(*args, **kwargs)

    def __getattr__(self, item):
        return getattr(self.client, item)

    @property
    def embeded_attributes(self):
        return self._embeded_attributes if isinstance(self._embeded_attributes, list) else []

    @cached_property
    def client(self):
        return Session(self._base_url)

    @property
    def request_kwargs(self):
        return self.client._request_kwargs

    @request_kwargs.setter
    def request_kwargs(self, request_kwargs):
        self.client._request_kwargs = request_kwargs

    def _apply_resource_attributes(self, instance, attributes):
        relationships = instance._relationships.keys()
        embeded_attributes = self.embeded_attributes

        for key, value in attributes.items():
            if key in relationships and key in embeded_attributes:
                instance._attributes[key] = value
                instance.dirty_fields.add(key)
            else:
                setattr(instance, key, value)
        return instance

    def update(self, instance, attributes):

        try:
            self._apply_resource_attributes(instance, attributes)
            instance.commit()

            return instance
        except DocumentError as ex:
            raise ex

    def create(self, resource_name, attributes):
        instance = self.client.create_and_commit(resource_name, attributes)
        logger.error(instance)
        return instance

    def add_model_schema(self, resource_name, properties):
        self.client.schema.add_model_schema({resource_name: {'properties': properties}})


