from payment_api.serializers import (
    CharField,
    IntegerField,
    ResourceMeta,
    ResourceSerializer
)


class WalletSerializer(ResourceSerializer):
    active = IntegerField(required=True)

    # "creationDate": 1550226586533,
    currency = CharField(required=True)
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
    iban = CharField(required=True)
    ibanGeneralPart = CharField(required=True)
    # "usedDate": 1553711346395

    class Meta(ResourceMeta):
        resource_name = 'wallets'




