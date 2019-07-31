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
    is_hidden = IntegerField(read_only=True, source='isHidden')
    amount = IntegerField(read_only=True)
    net_amount = IntegerField(read_only=True, source='netAmount')
    actual_balance = IntegerField(read_only=True, source='actualBalance')
    closing_balance = IntegerField(read_only=True, source='closingBalance')
    balance = IntegerField(read_only=True)
    execution_date = TimestampField(read_only=True, source='executionDate')
    completion_date = TimestampField(read_only=True, source='completionDate')
    name = CharField(read_only=True)
    reserved = IntegerField(read_only=True)
    reserved_amount = IntegerField(read_only=True, source='reservedAmount')
    instruction_amount = IntegerField(read_only=True, source='instructionAmount')
    fee_amount = IntegerField(read_only=True, source='feeAmount')
    status = CharField(read_only=True)
    creation_date = TimestampField(read_only=True, source='creationDate')
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





