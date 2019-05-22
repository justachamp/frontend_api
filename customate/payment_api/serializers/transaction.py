from payment_api.serializers import (
    UUIDField,
    CharField,
    IntegerField,
    ResourceMeta,
    JSONField,
    TimestampField,
    ResourceSerializer,
    ExternalResourceRelatedField
)


class TransactionSerializer(ResourceSerializer):
    included_serializers = {
        'payment': 'payment_api.serializers.PaymentSerializer',
        'origin': 'payment_api.serializers.FundingSourceSerializer',
        'recipient': 'payment_api.serializers.PayeeSerializer',
    }

    id = UUIDField(read_only=True)
    active = IntegerField(read_only=True)
    amount = IntegerField(read_only=True)
    actual_balance = IntegerField(read_only=True, source='actualBalance')
    balance = IntegerField(read_only=True)
    execution_date = TimestampField(read_only=True, source='executionDate')
    name = CharField(read_only=True)
    reserved = IntegerField(read_only=True)
    reservedAmount = IntegerField(read_only=True)
    fee_amount = IntegerField(read_only=True, source='feeAmount')
    status = CharField(read_only=True)
    update_date = TimestampField(read_only=True, source='updateDate')
    data = JSONField(read_only=True)
    payment = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='transaction-relationships',
    )

    origin = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='transaction-relationships'
    )

    recipient = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='transaction-relationships'
    )

    class Meta(ResourceMeta):
        resource_name = 'transactions'





