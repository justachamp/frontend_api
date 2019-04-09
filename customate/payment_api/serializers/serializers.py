from rest_framework_json_api import serializers
from payment_api.core.resource.fields import ExternalResourceRelatedField
from payment_api.core.resource.serializers import ResourceMeta, ResourceSerializer


class WalletSerializer(ResourceSerializer):
    active = serializers.IntegerField(required=True)

    # "creationDate": 1550226586533,
    currency = serializers.CharField(required=True)
    # "data": {
    #     "bank": {
    #         "zip": "20095",
    #         "city": "Hamburg",
    #         "name": "SAXO PAYMENTS",
    #         "address": "",
    #         "country": "Germany"
    #     },
    #     "account": {
    #         "bic": "SXPYDEHH",
    #         "sortCode": null,
    #         "accountNumber": null
    #     }
    # },
    iban = serializers.CharField(required=True)
    ibanGeneralPart = serializers.CharField(required=True)
    # "usedDate": 1553711346395

    # "id": "f73f0eb6-33c0-457e-b41c-6c970287ada6",
    # "attributes": {
    #     "active": 1,
    #     "creationDate": 1545388418695,
    #     "email": null,
    #     "updateDate": null
    # }

    class Meta(ResourceMeta):
        resource_name = 'wallets'


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
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(required=False)
    active = serializers.IntegerField(required=True)

    class Meta(ResourceMeta):
        resource_name = 'payment_accounts'




