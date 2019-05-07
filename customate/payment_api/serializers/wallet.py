from payment_api.serializers import (
    CharField,
    IntegerField,
    ResourceMeta,
    ResourceSerializer,
    TimestampField,
    ExternalResourceRelatedField,
    JSONField
)


class WalletSerializer(ResourceSerializer):
    included_serializers = {
        # 'external_service_accounts': 'payment_api.serializers.ExternalServiceAccountSerializer',
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
    balance = IntegerField(read_only=True)
    currency = CharField(required=True)
    iban = CharField(read_only=True)
    ibanGeneralPart = CharField(read_only=True)
    data = JSONField(read_only=True)
    used_date = TimestampField(read_only=True, source='usedDate')
    creation_date = TimestampField(read_only=True, source='creationDate')

    class Meta(ResourceMeta):
        resource_name = 'wallets'




