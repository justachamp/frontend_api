class ResourceMappingMixin:
    _resource_mapping = None

    def __init__(self, *args, **kwargs):
        self._resource_mapping = []
        if 'resource_mapping' in kwargs:
            self.resource_mapping = kwargs.pop('resource_mapping')
        return super().__init__(*args, **kwargs)

    @property
    def resource_mapping(self):
        return self._resource_mapping

    @resource_mapping.setter
    def resource_mapping(self, mapping):
        if isinstance(mapping, list):
            for item in mapping:
                self._resource_mapping.append(item)
        else:
            self._resource_mapping.append(mapping)

    def apply_mapping(self, resource):

        for item in self.resource_mapping:
            key = next(iter(item))
            data = item.get(key)
            if hasattr(resource, key):
                value = getattr(resource, key)
                op = data.get('op')
                if op == 'copy':
                    setattr(resource, data.get('value'), value)
                if op == 'edit':
                    setattr(resource, key, data.get('value'))
        return resource

    def reverse_mapping(self, resource):

        for item in self.resource_mapping:
            key = next(iter(item))
            data = item.get(key)
            if hasattr(resource, key):
                op = data.get('op')
                if op == 'copy' and hasattr(resource, data.get('value')):
                    resource._attributes.pop(data.get('value'), None)
                    resource._attributes._dirty_attributes.remove(data.get('value'))
                if op == 'edit':
                    setattr(resource, key, data.get('old_value'))

        return resource


class JsonApiErrorParser:

    def _parse_document_error(self, ex):
        try:
            resp = ex.response.json()
            errors = resp.get('errors')
            data = {}
            for error in errors:
                pointer = error.get('source', {}).get('pointer', '').split('/')[-1]
                if not data.get(pointer):
                    data[pointer] = []
                data[pointer].append(error.get('detail', ''))

            return data if len(data) else None
        except Exception:
            return None
