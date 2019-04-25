from rest_framework.permissions import AllowAny
from payment_api.serializers import FundingSourceSerializer

from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    ResourceRelationshipView,
    ResourceViewSet
)


class FundingSourceViewSet(ResourceViewSet):
    resource_name = 'funding_sources'
    allowed_methods = ['head', 'get']
    serializer_class = FundingSourceSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFiler,
        # ResourceFilterBackend,
        SearchFilter
    )


class FundingSourceRelationshipView(ResourceRelationshipView):
    serializer_class = FundingSourceSerializer
    resource_name = 'funding_sources'
