from payment_api.serializers import (
    UUIDField,
    CharField,
    ResourceMeta,
    JSONField,
    IntegerField,
    EnumField,
    TimestampField,
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
    data = JSONField(read_only=True)
    type = EnumField(enum=FundingSourceType, required=True, primitive_value=True, source='attributes.type',
                     result_source='type')
    title = CharField(read_only=True)

    payment_account = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='funding-source-related',
        self_link_view_name='funding-source-relationships',
        resource_mapping={'id': {'op': 'copy', 'value': 'pk'}},
        source='account'
    )

    class Meta(ResourceMeta):
        resource_name = 'funding_sources'

# {
#   "data": {
#     "type": "funding_sources",
#     "id": "223c7717-0655-4bde-9a3b-98be47d6abe7",
#     "attributes": {
#       "active": 1,
#       "creationDate": 1544029100400,
#       "data": {
#         "walletId": "5a382426-cd68-485e-8ed7-81e6f65efd1b",
#         "iban": "084caae1-d71c-48a3-bdfc-9c76326c6b1e",
#         "currency": "EUR"
#       },
#       "title": "Test Funding Source",
#       "type": "WALLET"
#     },
#     "relationships": {
#       "account": {
#         "data": {
#           "type": "accounts",
#           "id": "dedf7a91-f113-4977-a02b-440ed766a962"
#         }
#       }
#     }
#   }
# }
