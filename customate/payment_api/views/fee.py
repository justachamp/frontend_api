from rest_framework.permissions import AllowAny
from payment_api.serializers import FeeGroupSerializer


from payment_api.views import (
    InclusionFiler,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    RelationshipView,
    ResourceViewSet
)


class FeeGroupViewSet(ResourceViewSet):
    resource_name = 'fee_groups'
    serializer_class = FeeGroupSerializer
    permission_classes = (AllowAny,)
    filter_backends = (
        QueryParameterValidationFilter,
        OrderingFilter,
        InclusionFiler,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'active': ('exact',),
        'title': ('exact', 'contains', 'startswith', 'endswith'),
    }

    class Meta:
        include_resources = ['fees']
        embedded_resources = ['fees']
        filters = [{'active__exact': 1}]


class FeeGroupRelationshipView(RelationshipView):
    serializer_class = FeeGroupSerializer
    resource_name = 'fee_groups'

    def get_queryset(self):
        pass
