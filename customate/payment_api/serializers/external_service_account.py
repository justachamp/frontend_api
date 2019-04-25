from payment_api.serializers import (
    CharField,
    IntegerField,
    ResourceMeta,
    ResourceSerializer
)


class ExternalServiceAccountSerializer(ResourceSerializer):

    class Meta(ResourceMeta):
        resource_name = 'external_service_account'




