from payment_api.serializers import (
    IbanField,
    CharField,
    TypeEnumField,
    IntegerField,
    EnumField,
    ResourceMeta,
    ResourceSerializer,
    Currency,
    PayeeType,
    ExternalResourceRelatedField,
    JSONField
)


class BasePayeeSerializer(ResourceSerializer):
    title = CharField(required=True)
    active = IntegerField(read_only=True)

    class Meta(ResourceMeta):
        resource_name = 'payees'


class PayeeSerializer(BasePayeeSerializer):
    included_serializers = {
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer'
    }

    payment_account = ExternalResourceRelatedField(
        required=True,
        related_link_view_name='payee-related',
        self_link_view_name='payee-relationships',
        source='account'
    )

    type = TypeEnumField(enum=PayeeType, required=True, primitive_value=True)
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    data = JSONField(required=True)


class UpdatePayeeSerializer(BasePayeeSerializer):
    type = TypeEnumField(enum=PayeeType, primitive_value=True, read_only=True)
    currency = EnumField(enum=Currency, primitive_value=True, read_only=True)
    data = JSONField(read_only=True)



