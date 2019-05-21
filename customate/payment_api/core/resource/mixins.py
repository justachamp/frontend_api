class ResourceMappingMixin:
    _resource_mapping = None

    def __init__(self, *args, **kwargs):
        if 'resource_mapping' in kwargs:
            self.resource_mapping = kwargs.pop('resource_mapping')
        return super().__init__(*args, **kwargs)

    @property
    def resource_mapping(self):
        if not self._resource_mapping:
            self._resource_mapping = []
        return self._resource_mapping

    @resource_mapping.setter
    def resource_mapping(self, mapping):
        if isinstance(mapping, list):
            for item in mapping:
                self.resource_mapping.append(item)
        else:
            self.resource_mapping.append(mapping)

    def key_mapping(self, data, keys):
        for old_key, new_key in keys.items():
            data[new_key] = data.pop(old_key)

    def apply_mapping(self, resource):
        map_attr = self._get_mapping_strategy('apply', resource)
        for item in self.resource_mapping:
            key = next(iter(item))
            data = item.get(key)
            map_attr(key, data, resource)

        return resource

    def _get_mapping_strategy(self, action, resource):
        return getattr(self, f'_{action}_{"data" if isinstance(resource, dict) else "instance"}_mapping')

    def _hasattr(self, resource, key):
        return (hasattr(resource, '_attributes') and key in resource._attributes) or\
               (hasattr(resource, '_relationships') and key in resource._relationships)

    def _getattr(self, resource, key, def_val=None):

        if key in resource._attributes:
            return resource._attributes[key]

        elif key in resource._relationships:
            return resource._relationships[key]
        else:
            return def_val

    def _apply_instance_mapping(self, key, data, resource):
        op = data.get('op')
        if op == 'map' and self._hasattr(resource, data.get('value')):
            attribute_key = data.get('value')
            value = self._getattr(resource, attribute_key, None)

            if attribute_key in resource._attributes:
                resource._attributes.pop(attribute_key, None)
                self._attributes[key] = value
            elif attribute_key in resource._relationships:
                resource._relationships.pop(attribute_key, None)
                resource._relationships[key] = value

            if attribute_key in resource._attributes._dirty_attributes:
                resource._attributes._dirty_attributes.remove(attribute_key)

            if key in resource._attributes._dirty_attributes:
                resource._attributes._dirty_attributes.remove(key)

        elif op == 'custom' and callable(data.get('value')):
            data.get('value')(resource)

        elif hasattr(resource, key):
            value = getattr(resource, key)
            if op == 'copy':
                setattr(resource, data.get('value'), value)
            elif op == 'edit':
                setattr(resource, key, data.get('value'))

    def _apply_data_mapping(self, key, data, resource):
        op = data.get('op')
        if op == 'map' and resource.get(data.get('value')):
            value = resource.pop(data.get('value'), None)
            resource[key] = value
        elif key in resource:
            value = resource.get(key)
            if op == 'copy':
                resource[data.get('value')] = value
            elif op == 'edit':
                resource[key] = data.get('value')

    def reverse_mapping(self, resource):
        mapping_strategy = self._get_mapping_strategy('reverse', resource)
        for item in self.resource_mapping:
            key = next(iter(item))
            data = item.get(key)
            mapping_strategy(key, data, resource)
        return resource

    def _reverse_instance_mapping(self, key, data, resource):
        if hasattr(resource, key):
            op = data.get('op')
            if op == 'copy' and hasattr(resource, data.get('value')):
                resource._attributes.pop(data.get('value'), None)
                resource._attributes._dirty_attributes.remove(data.get('value'))
            if op == 'map':
                value = resource._attributes.pop(key, None)
                setattr(resource, data.get('value'), value)
                if key in resource._attributes._dirty_attributes:
                    resource._attributes._dirty_attributes.remove(key)
                else:
                    if data.get('value') in resource._attributes._dirty_attributes:
                        resource._attributes._dirty_attributes.remove(data.get('value'))

            if op == 'edit':
                setattr(resource, key, data.get('old_value'))


    def _reverse_data_mapping(self, key, data, resource):
        if key in resource:
            op = data.get('op')
            if op == 'copy' and data.get('value') in resource:
                resource.pop(data.get('value'))
            elif op == 'map':
                value = resource.pop(key, None)
                resource[data.get('value')] = value
            elif op == 'edit':
                resource[key] = data.get('old_value')


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
