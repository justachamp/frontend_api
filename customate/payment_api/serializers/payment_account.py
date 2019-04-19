from payment_api.serializers import (
    UUIDField,
    EmailField,
    IntegerField,
    ExternalResourceRelatedField,
    ResourceMeta,
    ResourceSerializer
)


class PaymentAccountSerializer(ResourceSerializer):

    included_serializers = {
        'wallets': 'payment_api.serializers.WalletSerializer'
    }

    wallets = ExternalResourceRelatedField(
        many=True,
        # read_only=True,
        required=False,
        related_link_view_name='payment-account-related',
        self_link_view_name='payment-account-relationships',
        resource_mapping={'id': {'op': 'copy', 'value': 'pk'}}
    )

    # "id": "f73f0eb6-33c0-457e-b41c-6c970287ada6",
    # "attributes": {
    #     "active": 1,
    #     "creationDate": 1545388418695,
    #     "email": null,
    #     "updateDate": null
    # }
    id = UUIDField(read_only=True)
    email = EmailField(required=False)
    active = IntegerField(read_only=True)

    class Meta(ResourceMeta):
        resource_name = 'payment_accounts'




