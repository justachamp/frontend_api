from rest_framework_json_api.serializers import ChoiceField

from rest_framework_json_api.relations import ResourceRelatedField, PolymorphicResourceRelatedField


class ResourceRelatedField(ResourceRelatedField):

    def use_pk_only_optimization(self):
        # TODO workaround
        #  Original exception text was: 'PKOnlyObject' object has no attribute 'address'.
        return False


class EnumField(ChoiceField):
    def __init__(self, enum, value_field='value', **kwargs):
        self.enum = enum
        self.value_field = value_field

        kwargs['choices'] = [(e.name, getattr(e, value_field)) for e in enum]
        super(EnumField, self).__init__(**kwargs)

    def to_representation(self, obj):
        return getattr(obj, self.value_field)

    def to_internal_value(self, data):
        try:
            return self.enum[data]
        except KeyError:
            self.fail('invalid_choice', input=data)