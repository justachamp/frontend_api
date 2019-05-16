from rest_framework.permissions import AllowAny

from payment_api.serializers import (
    IbanValidationSerializer, SortCodeAccountNumberValidationSerializer, CheckGBSerializer
)

from payment_api.views import (
    ResourceViewSet
)


class IbanValidationViewSet(ResourceViewSet):
    resource_name = 'ibans'
    permission_classes = (AllowAny,)

    def get_serializer_class(self):
        is_gb = CheckGBSerializer(data=self.request.data).is_valid(False)
        return SortCodeAccountNumberValidationSerializer if is_gb else IbanValidationSerializer

    class Meta:
        resource_suffix_name = 'validation'
