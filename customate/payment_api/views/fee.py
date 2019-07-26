from rest_framework.permissions import IsAuthenticated
from frontend_api.permissions import IsSuperAdminOrReadOnly, AdminUserFeePermission
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
    permission_classes = (  IsAuthenticated,
                            IsSuperAdminOrReadOnly|
                            AdminUserFeePermission, )
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
    permission_classes = (IsAuthenticated,)
    # filter_backends = (
    #     QueryParameterValidationFilter,
    #     OrderingFilter,
    #     InclusionFiler,
    #     ResourceFilterBackend,
    #     SearchFilter
    # )
    #
    # filterset_fields = {
    #     'active': ('exact',),
    #     'title': ('exact', 'contains', 'startswith', 'endswith'),
    # }
    # payment account id dab09dfe-080d-482a-ab17-6837c80ad66f
    # data_key_mapping = {'fee_groups': 'feeGroup', 'accounts': 'account'}
    class Meta:
        resource_mapping = [
            {'fee_groups': {'op': 'map', 'value': 'feeGroup'}},
            {'accounts': {'op': 'map', 'value': 'account'}}
        ]


class FeeGroupAccountRelationshipView(ResourceRelationshipView):
    resource_name = 'fee_group_accounts'
    serializer_class = FeeGroupAccountSerializer
