from payment_api.serializers import (
    UUIDField,
    EnumField,
    FloatField,
    IntegerField,
    IbanField,
    Country,
    ResourceMeta,
    ResourceSerializer
)


class TaxSerializer(ResourceSerializer):
    id = UUIDField(read_only=True)
    is_default = IntegerField(required=True, source='isDefault')
    country = EnumField(enum=Country, required=True, primitive_value=True)
    active = IntegerField(read_only=True)
    fee_iban = IbanField(required=True, source='feeIban')
    tax_iban = IbanField(required=True, source='taxIban')
    percent = FloatField(min_value=0, max_value=100)

    class Meta(ResourceMeta):
        resource_name = 'taxes'




