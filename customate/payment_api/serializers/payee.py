from payment_api.serializers import (
    IbanField,
    IntegerField,
    EnumField,
    ResourceMeta,
    ResourceSerializer,
    Currency,
    PayeeType,
    ExternalResourceRelatedField,
    JSONField
)


class PayeeSerializer(ResourceSerializer):
    included_serializers = {
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer'
    }

    payment_account = ExternalResourceRelatedField(
        read_only=True,
        required=False,
        related_link_view_name='wallet-related',
        self_link_view_name='wallet-relationships',
        source='account'
    )

    active = IntegerField(read_only=True)
    type = EnumField(enum=PayeeType, required=True, primitive_value=True, source='attributes.type',
                     result_source='type')
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    iban = IbanField(read_only=True)
    data = JSONField(read_only=True)

    class Meta(ResourceMeta):
        resource_name = 'payees'




