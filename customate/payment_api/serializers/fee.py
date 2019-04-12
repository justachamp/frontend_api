from payment_api.serializers import (
    UUIDField,
    EmailField,
    IntegerField,
    FloatField,
    CharField,
    ExternalResourceRelatedField,
    ResourceMeta,
    ResourceSerializer,
    Serializer,
    EnumField,
    FeeType,
    OperationType
)

from core.fields import SerializerField


class EmbededFeeSerializer(Serializer):
    id = UUIDField(primitive_value=True)
    fixed_value = IntegerField(min_value=0, source='fixedValue')
    index_number = IntegerField(min_value=0, read_only=True, source='indexNumber')
    max = IntegerField(min_value=0)
    min = IntegerField(min_value=0)
    operation = EnumField(enum=OperationType, required=True, primitive_value=True)
    percent = FloatField(min_value=0, max_value=100)
    type = EnumField(enum=FeeType, required=True, primitive_value=True, source='attributes.type', result_source='type')
    use_default = IntegerField(source='useDefault')


class FeeSerializer(ResourceSerializer):
    id = UUIDField()
    fixed_value = IntegerField(min_value=0, source='fixedValue')
    index_number = IntegerField(min_value=0, read_only=True, source='indexNumber')
    max = IntegerField(min_value=0)
    min = IntegerField(min_value=0)
    operation = EnumField(enum=OperationType, required=True)
    percent = FloatField(min_value=0, max_value=100)
    fee_type = EnumField(enum=FeeType, required=True, source='type')
    use_default = IntegerField(source='useDefault')

    class Meta(ResourceMeta):
        resource_name = 'fees'


# address = SerializerField(resource=UserAddressSerializer, required=False)
class FeeGroupSerializer(ResourceSerializer):
    included_serializers = {
        'fees': 'payment_api.serializers.FeeSerializer'
    }

    id = UUIDField(read_only=True)
    is_default = IntegerField(required=True, source='isDefault')
    title = CharField(required=True)
    # fees = ExternalResourceRelatedField(
    #     many=True,
    #     # read_only=True,
    #     required=False,
    #     related_link_view_name='fee-group-related',
    #     self_link_view_name='fee-group-relationships',
    #     resource_mapping={'id': {'op': 'copy', 'value': 'pk'}}
    # )
    fees = SerializerField(resource=EmbededFeeSerializer, many=True)

    class Meta(ResourceMeta):
        resource_name = 'fee_groups'
