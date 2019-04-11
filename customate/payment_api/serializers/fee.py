from payment_api.serializers import (
    UUIDField,
    EmailField,
    IntegerField,
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
    id = UUIDField(read_only=True)
    fixed_value = IntegerField(min_value=0, source='fixedValue')
    index_number = IntegerField(min_value=0, read_only=True, source='indexNumber')
    max = IntegerField(min_value=0)
    min = IntegerField(min_value=0)
    operation = EnumField(enum=OperationType, required=True, primitive_value=True)
    percent = IntegerField(min_value=0, max_value=100)
    type = EnumField(enum=FeeType, required=True, primitive_value=True, source='attributes.type', result_source='type')
    user_default = IntegerField(read_only=True, source='userDefault')


class FeeSerializer(ResourceSerializer):
    id = UUIDField(read_only=True)
    fixed_value = IntegerField(min_value=0, source='fixedValue')
    index_number = IntegerField(min_value=0, read_only=True, source='indexNumber')
    max = IntegerField(min_value=0)
    min = IntegerField(min_value=0)
    operation = EnumField(enum=OperationType, required=True)
    percent = IntegerField(min_value=0, max_value=100)
    fee_type = EnumField(enum=FeeType, required=True, source='type')
    user_default = IntegerField(read_only=True, source='userDefault')

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
    fees = SerializerField(resource=EmbededFeeSerializer)

    class Meta(ResourceMeta):
        resource_name = 'fee_groups'





















{
  "data": {
    "type": "fee_groups",
    "attributes": {
      "isDefault": 0,
      "title": "New Fee Group",
      "fees": [
        {
          "active": 1,
          "fixedValue": 100,
          "indexNumber": 0,
          "max": 500,
          "min": 100,
          "operation": "DEFAULT",
          "percent": 1,
          "type": "STATIC",
          "useDefault": 0
        },
        {
          "active": 1,
          "fixedValue": 0,
          "indexNumber": 1,
          "max": 0,
          "min": 0,
          "operation": "MONEY_IN_DD",
          "percent": 0,
          "type": "STATIC",
          "useDefault": 1
        },
        {
          "active": 1,
          "fixedValue": 0,
          "indexNumber": 2,
          "max": 0,
          "min": 0,
          "operation": "MONEY_IN_CC",
          "percent": 0,
          "type": "STATIC",
          "useDefault": 1
        },
        {
          "active": 1,
          "fixedValue": 0,
          "indexNumber": 3,
          "max": 0,
          "min": 0,
          "operation": "MONEY_IN_BT",
          "percent": 0,
          "type": "STATIC",
          "useDefault": 1
        },
        {
          "active": 1,
          "fixedValue": 0,
          "indexNumber": 4,
          "max": 0,
          "min": 0,
          "operation": "MONEY_OUT_BT",
          "percent": 0,
          "type": "STATIC",
          "useDefault": 1
        },
        {
          "active": 1,
          "fixedValue": 100,
          "indexNumber": 5,
          "max": 500,
          "min": 100,
          "operation": "INTERNAL",
          "percent": 1,
          "type": "PERCENTAGE",
          "useDefault": 0
        }
      ]
    }
  }
}