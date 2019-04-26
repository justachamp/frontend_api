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
        'origin_funding_source': 'payment_api.serializers.FundingSourceSerializer',
        'recipient_funding_source': 'payment_api.serializers.FundingSourceSerializer',
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

    origin_funding_source = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='payment-relationships',
        source='originFundingSource'
    )

    recipient_funding_source = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='payment-relationships',
        source='recipientFundingSource'
    )

    class Meta(ResourceMeta):
        resource_name = 'payments'





