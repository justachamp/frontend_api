from payment_api.serializers import (
    CharField,
    IntegerField,
    ResourceMeta,
    ResourceSerializer,
    TimestampField,
    JSONField
)


class WalletSerializer(ResourceSerializer):
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




