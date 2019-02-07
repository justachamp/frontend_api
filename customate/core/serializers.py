
class BulkExtensionMixin(object):
    def get_serializer(self, *args, **kwargs):
        is_bulk = isinstance(self.request.data, list)
        kwargs['many'] = kwargs.pop('many', is_bulk)
        return super().get_serializer(*args, **kwargs)