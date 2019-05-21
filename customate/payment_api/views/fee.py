from rest_framework.permissions import AllowAny
from payment_api.serializers import FeeGroupSerializer, FeeGroupAccountSerializer


from payment_api.views import (
    InclusionFilter,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet
)


class FeeGroupViewSet(ResourceViewSet):
    resource_name = 'fee_groups'
    serializer_class = FeeGroupSerializer
    permission_classes = (AllowAny,)
    filter_backends = (
        QueryParameterValidationFilter,
        OrderingFilter,
        InclusionFilter,
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


class FeeGroupRelationshipView(ResourceRelationshipView):
    serializer_class = FeeGroupSerializer
    resource_name = 'fee_groups'


class FeeGroupAccountViewSet(ResourceViewSet):
    resource_name = 'fee_group_accounts'
    serializer_class = FeeGroupAccountSerializer
    permission_classes = (AllowAny,)


class FeeGroupAccountRelationshipView(ResourceRelationshipView):
    resource_name = 'fee_group_accounts'
    serializer_class = FeeGroupAccountSerializer
