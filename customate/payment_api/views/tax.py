from rest_framework.permissions import AllowAny
from payment_api.serializers import TaxSerializer

from payment_api.views import (
    InclusionFiler,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
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
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'active': ('exact',)
    }

    class Meta:
        filters = [{'active__exact': 1}]


class TaxRelationshipView(RelationshipView):
    resource_name = 'taxes'
    serializer_class = TaxSerializer

    def get_queryset(self):
        pass
