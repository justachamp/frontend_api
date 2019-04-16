from rest_framework.permissions import AllowAny
from payment_api.serializers import TaxSerializer

from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    RelationshipView,
    ResourceViewSet
)


class TaxViewSet(ResourceViewSet):
    resource_name = 'taxes'
    serializer_class = TaxSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFiler,
        # ResourceFilterBackend,
        SearchFilter
    )


class TaxRelationshipView(RelationshipView):
    resource_name = 'taxes'
    serializer_class = TaxSerializer

    def get_queryset(self):
        pass
