from payment_api.serializers import (
    UUIDField,
    CharField,
    IntegerField,
    ResourceMeta,
    JSONField,
    TimestampField,
    ResourceSerializer
)


class TransactionSerializer(ResourceSerializer):
    id = UUIDField(read_only=True)
    amount = IntegerField(read_only=True)
    balance = IntegerField(read_only=True)
    execution_date = TimestampField(read_only=True, source='executionDate')
    name = CharField(read_only=True)
    reserved = IntegerField(read_only=True)
    reservedAmount = IntegerField(read_only=True)
    status = CharField(read_only=True)
    update_date = TimestampField(read_only=True, source='updateDate')
    data = JSONField(read_only=True)

    class Meta(ResourceMeta):
        resource_name = 'transactions'





