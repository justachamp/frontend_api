from payment_api.serializers import (
    UUIDField,
    EmailField,
    IntegerField,
    ExternalResourceRelatedField,
    TimestampField,
    CharField,
    ResourceMeta,
    ResourceSerializer
)


class PaymentAccountSerializer(ResourceSerializer):

    included_serializers = {
        # 'external_service_accounts': 'payment_api.serializers.ExternalServiceAccountSerializer',
        'fee_group': 'payment_api.serializers.FeeGroupSerializer',
        'funding_sources': 'payment_api.serializers.FundingSourceSerializer',
        'tax': 'payment_api.serializers.TaxSerializer',
        'wallets': 'payment_api.serializers.WalletSerializer'
    }
    #
    # external_service_accounts = ExternalResourceRelatedField(
    #
    #     read_only=True,
    #     required=False,
    #     related_link_view_name='payment-account-related',
    #     self_link_view_name='payment-account-relationships',
    #     source='externalServiceAccounts'
    # )

    fee_group = ExternalResourceRelatedField(
        read_only=True,
        required=False,
        related_link_view_name='payment-account-related',
        self_link_view_name='payment-account-relationships',
        source='feeGroup'
    )

    funding_sources = ExternalResourceRelatedField(
        many=True,
        read_only=True,
        required=False,
        related_link_view_name='payment-account-related',
        self_link_view_name='payment-account-relationships',
        source='fundingSources'
    )

    wallets = ExternalResourceRelatedField(
        many=True,
        read_only=True,
        required=False,
        related_link_view_name='payment-account-related',
        self_link_view_name='payment-account-relationships',
    )

    id = UUIDField(read_only=True)
    original_account_id = UUIDField(source='originalAccountId')
    email = EmailField(required=False)
    full_name = CharField(required=True, source='fullName')
    active = IntegerField(read_only=True)
    update_date = TimestampField(read_only=True, source='updateDate')
    creation_date = TimestampField(read_only=True, source='creationDate')

    class Meta(ResourceMeta):
        resource_name = 'payment_accounts'




