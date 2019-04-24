from payment_api.serializers import (
    UUIDField,
    EnumField,
    FloatField,
    IntegerField,
    IbanField,
    TimestampField,
    Currency,
    Serializer,
    ResourceMeta,
    ResourceSerializer
)

from core.fields import SerializerField


class TaxSerializer(ResourceSerializer):
    id = UUIDField(read_only=True)
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    active = IntegerField(read_only=True)
    fee_iban = IbanField(required=True, source='feeIban')
    tax_iban = IbanField(required=True, source='taxIban')
    percent = FloatField(min_value=0, max_value=100)
    creation_date = TimestampField(read_only=True, source='creationDate')

    class Meta(ResourceMeta):
        resource_name = 'taxes'


class EmbededTaxSerializer(Serializer):
    id = UUIDField(primitive_value=True)
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    active = IntegerField(read_only=True)
    fee_iban = IbanField(read_only=True, source='feeIban')
    tax_iban = IbanField(read_only=True, source='taxIban')
    percent = FloatField(min_value=0, max_value=100)
    creation_date = TimestampField(read_only=True, source='creationDate')


class TaxGroupSerializer(ResourceSerializer):
    included_serializers = {
        'taxes': 'payment_api.serializers.TaxSerializer'
    }

    id = UUIDField(read_only=True)
    taxes = SerializerField(resource=EmbededTaxSerializer, many=True)

    class Meta(ResourceMeta):
        resource_name = 'tax_groups'




