from jsonapi_client import Session as DefaultSession, Filter, ResourceTuple, Modifier
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

models_as_jsonschema = {
    'identity': {'properties': {
    }}
}


class Session(DefaultSession):
    def _get_sync(self, resource_type: str,
                  resource_id_or_filter: 'Union[Modifier, str]'=None) -> 'Document':
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


class Client:

    _client = None
    _base_url = None

    def __init__(self, base_url):
        self._base_url = base_url
        self._resource_mapping = []

    def __getattr__(self, item):
        return getattr(self.client, item)


    @property
    def client(self):
        if not self._client:
            self._client = Session(self._base_url, schema=models_as_jsonschema)

        return self._client
    @property
    def request_kwargs(self):
        return self.client._request_kwargs

    @request_kwargs.setter
    def request_kwargs(self, request_kwargs):
        self.client._request_kwargs = request_kwargs


    @property
    def resource_mapping(self):
        return self._resource_mapping

    @resource_mapping.setter
    def resource_mapping(self, resource_mapping):
        self._resource_mapping.append(resource_mapping)

    def _apply_resource_attributes(self, instance, attributes):
        for key, value in attributes.items():
            setattr(instance, key, value)
        return instance

    def update(self, instance, attributes):

        self._apply_resource_attributes(instance, attributes)
        instance.commit()

        return instance

    def create(self, resource_name, attributes):
        self._generate_resource_schema(resource_name)
        instance = self.client.create_and_commit(resource_name, attributes)
        logger.error(instance)
        return instance

    def add_model_schema(self, resource_name, properties):
        self.client.schema.add_model_schema({resource_name: {'properties': properties}})

    # def _generate_resource_schema(self, resource_name):
    #     self.client.schema.add_model_schema({resource_name: {'properties': {
    #         'wallets': {'relation': 'to-many', 'resource': ['wallets']},
    #     }}})

