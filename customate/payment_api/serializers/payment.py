from payment_api.serializers import (
    UUIDField,
    CharField,
    ResourceMeta,
    JSONField,
    TimestampField,
    ResourceSerializer,
    ExternalResourceRelatedField
)


class PaymentSerializer(ResourceSerializer):
    included_serializers = {
        'transactions': 'payment_api.serializers.TransactionSerializer'
    }

    id = UUIDField(read_only=True)
    contract_id = UUIDField(read_only=True)
    creation_date = TimestampField(read_only=True, source='creationDate')
    currency = CharField(read_only=True)
    scenario = CharField(read_only=True),
    status = CharField(read_only=True),
    updateDate = TimestampField(read_only=True, source='updateDate'),
    userId = UUIDField(read_only=True)
    data = JSONField(read_only=True)
    transactions = ExternalResourceRelatedField(
        many=True,
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
        resource_mapping={'id': {'op': 'copy', 'value': 'pk'}}
    )

    class Meta(ResourceMeta):
        resource_name = 'payments'





