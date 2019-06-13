import logging
from payment_api.serializers import (
    UUIDField,
    CharField,
    ResourceMeta,
    JSONField,
    EnumField,
    TypeEnumField,
    Currency,
    FundingSourceType,
    FundingSourceStatus,
    ResourceSerializer,
    ExternalResourceRelatedField
)

logger = logging.getLogger(__name__)


class BaseFundingSourceSerializer(ResourceSerializer):
    title = CharField(required=True)

    class Meta(ResourceMeta):
        resource_name = 'funding_sources'


class FundingSourceSerializer(BaseFundingSourceSerializer):
    included_serializers = {
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer'
    }

    type = TypeEnumField(enum=FundingSourceType, required=True, primitive_value=True)
    status = EnumField(enum=FundingSourceStatus, required=False, primitive_value=True)
    validation_message = CharField(required=False, source='validationMessage')
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    data = JSONField(required=True)
    address = JSONField(required=False)
    payment_account = ExternalResourceRelatedField(
        required=True,
        related_link_view_name='funding-source-related',
        self_link_view_name='funding-source-relationships',
        source='account'
    )

    def validate(self, data):
        logger.info("VALIDATE, data=%r" % data)
        self.service.validate_source(data)
        return data

    class Meta(ResourceMeta):
        service = 'payment_api.services.FundingSourcesRequestResourceService'
        resource_name = 'funding_sources'


class UpdateFundingSourceSerializer(BaseFundingSourceSerializer):
    type = TypeEnumField(enum=FundingSourceType, primitive_value=True, read_only=True)
    currency = EnumField(enum=Currency, primitive_value=True, read_only=True)
    data = JSONField(read_only=True)
