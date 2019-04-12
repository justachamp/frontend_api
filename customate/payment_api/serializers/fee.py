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


{
    "data": {
        "type": "fee_groups",
        "id": "72f99e27-f9f3-48b6-9826-d181167c8a61",
        "attributes": {
            "active": 1,
            "creationDate": 1553855321551,
            "is_default": 0,
            "title": "New Fee Group",
            "fees": [
                {
                    "id": "db25de33-d4d6-499f-ab4b-37b98351785a",
                    "active": 1,
                    "fixed_value": 100,
                    "index_number": 0,
                    "max": 500,
                    "min": 100,
                    "operation": "DEFAULT",
                    "percent": 1,
                    "type": "STATIC",
                    "use_default": 0
                },
                {
                    "id": "e79fcd2e-470d-4371-ae95-8c02fba3b78b",
                    "active": 1,
                    "fixed_value": 0,
                    "index_number": 1,
                    "max": 0,
                    "min": 0,
                    "operation": "MONEY_IN_DD",
                    "percent": 0,
                    "type": "STATIC",
                    "use_default": 1
                },
                {
                    "id": "5ea65eff-14a6-4d80-b466-35b57b5c8187",
                    "active": 1,
                    "fixed_value": 0,
                    "index_number": 2,
                    "max": 0,
                    "min": 0,
                    "operation": "MONEY_IN_CC",
                    "percent": 0,
                    "type": "STATIC",
                    "use_default": 1
                },
                {
                    "id": "6b8e1667-db40-4683-8d06-2cab29642c33",
                    "active": 1,
                    "fixed_value": 0,
                    "index_number": 3,
                    "max": 0,
                    "min": 0,
                    "operation": "MONEY_IN_BT",
                    "percent": 0,
                    "type": "STATIC",
                    "use_default": 1
                },
                {
                    "id": "c8112bee-6b88-4300-988a-332051586abe",
                    "active": 1,
                    "fixed_value": 0,
                    "index_number": 4,
                    "max": 0,
                    "min": 0,
                    "operation": "MONEY_OUT_BT",
                    "percent": 0,
                    "type": "STATIC",
                    "use_default": 1
                },
                {
                    "id": "97f1fe5b-4e81-477b-982e-3ea551a3051a",
                    "active": 1,
                    "fixed_value": 100,
                    "index_number": 5,
                    "max": 500,
                    "min": 100,
                    "operation": "INTERNAL",
                    "percent": 1,
                    "type": "PERCENTAGE",
                    "use_default": 0
                }
            ]
        }
    }
}



{'data': {
    'type': 'fee_groups',
    'id': '72f99e27-f9f3-48b6-9826-d181167c8a61',
          'attributes': {'fees': [
    {
        'id': 'db25de33-d4d6-499f-ab4b-37b98351785a',
        'fixedValue': 100,
        'max': 500,
        'min': 100,
        'operation': 'Default',
        'percent': 1.0,
        'type': 'Static',
        'useDefault': 0
    },
    {'id': 'e79fcd2e-470d-4371-ae95-8c02fba3b78b', 'fixedValue': 0, 'max': 0, 'min': 0,
     'operation': 'Income direct debit', 'percent': 0.0, 'type': 'Static', 'useDefault': 1},
    {'id': '5ea65eff-14a6-4d80-b466-35b57b5c8187', 'fixedValue': 0, 'max': 0, 'min': 0,
     'operation': 'Income credit card', 'percent': 0.0, 'type': 'Static', 'useDefault': 1},
    {'id': '6b8e1667-db40-4683-8d06-2cab29642c33', 'fixedValue': 0, 'max': 0, 'min': 0,
     'operation': 'Income bank transfer', 'percent': 0.0, 'type': 'Static', 'useDefault': 1},
    {'id': 'c8112bee-6b88-4300-988a-332051586abe', 'fixedValue': 0, 'max': 0, 'min': 0,
     'operation': 'Outcome bank transfer', 'percent': 0.0, 'type': 'Static', 'useDefault': 1},
    {'id': '97f1fe5b-4e81-477b-982e-3ea551a3051a', 'fixedValue': 100, 'max': 500, 'min': 100, 'operation': 'Internal',
     'percent': 1.0, 'type': 'Percentage', 'useDefault': 0}]}, 'relationships': {}}
 }
