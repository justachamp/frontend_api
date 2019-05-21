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
        'transactions': 'payment_api.serializers.TransactionSerializer',
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer',
        'origin': 'payment_api.serializers.FundingSourceSerializer',
        'recipient': 'payment_api.serializers.PayeeSerializer',
    }

    id = UUIDField(read_only=True)
    contract_id = UUIDField(read_only=True, source='contractId')
    creation_date = TimestampField(read_only=True, source='creationDate')
    currency = CharField(read_only=True)
    scenario = CharField(read_only=True),
    status = CharField(read_only=True),
    update_date = TimestampField(read_only=True, source='updateDate'),
    userId = UUIDField(read_only=True)
    data = JSONField(read_only=True)
    transactions = ExternalResourceRelatedField(
        many=True,
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
    )

    payment_account = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
        source='account'
    )

    origin = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='payment-relationships'
    )

    recipient = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='payment-relationships'
    )

    class Meta(ResourceMeta):
        resource_name = 'payments'





