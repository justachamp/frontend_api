from frontend_api.permissions import IsSuperAdminOrReadOnly, AdminUserTaxPermission
from payment_api.serializers import TaxSerializer, TaxGroupSerializer

from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet
)


class TaxViewSet(ResourceViewSet):
    resource_name = 'taxes'
    serializer_class = TaxSerializer
    permission_classes = ()

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'active': ('exact',)
    }

    class Meta:
        filters = [{'active__exact': 1}]


class TaxRelationshipView(ResourceRelationshipView):
    resource_name = 'taxes'
    serializer_class = TaxSerializer


class TaxGroupViewSet(ResourceViewSet):
    resource_name = 'tax_groups'
    serializer_class = TaxGroupSerializer
    permission_classes = (IsSuperAdminOrReadOnly|AdminUserTaxPermission,)
    filter_backends = (
        OrderingFilter,
        InclusionFilter
    )

    class Meta:
        include_resources = ['taxes']
        embedded_resources = ['taxes']


class TaxGroupRelationshipView(ResourceRelationshipView):
    serializer_class = TaxGroupSerializer
    resource_name = 'tax_groups'
