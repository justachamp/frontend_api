from payment_api.serializers import (
    UUIDField,
    CharField,
    ResourceMeta,
    JSONField,
    EnumField,
    IntegerField,
    TypeEnumField,
    TimestampField,
    Currency,
    FundingSourceType,
    ResourceSerializer,
    ExternalResourceRelatedField
)


class FundingSourceSerializer(ResourceSerializer):
    included_serializers = {
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer'
    }

    id = UUIDField(read_only=True)
    active = IntegerField(read_only=True)
    creation_date = TimestampField(read_only=True, source='creationDate')
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    data = JSONField(read_only=True)
    title = CharField(read_only=True)
    type = TypeEnumField(enum=FundingSourceType, required=True, primitive_value=True)

    payment_account = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='funding-source-related',
        self_link_view_name='funding-source-relationships',
        source='account'
    )

    class Meta(ResourceMeta):
        resource_name = 'funding_sources'
