class FlexFieldsJsonFieldSerializerMixin(object):

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        key = self.additional_key
        if hasattr(self.Meta, 'additional_fields') and key in self.Meta.additional_fields:
            for key, value in self.Meta.additional_fields[key].items():
                self.fields[key] = value
