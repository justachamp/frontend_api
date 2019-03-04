class FlexFieldsSerializerMixin(object):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        for key in self.__extract_additional_key():
            self.__attach_fields(key)

    def __attach_fields(self, key):
        if hasattr(self.Meta, 'additional_fields') and key in self.Meta.additional_fields:
            for key, value in self.Meta.additional_fields[key].items():
                if value.source == key:
                    # @TODO check where additional fields has source == key assign
                    # @TODO workaround
                    value.source = None
                self.fields[key] = value

    def __extract_additional_key(self):
        key = self.additional_key

        if isinstance(key, list):
            for item_key in key:
                yield item_key
        else:
            yield key
