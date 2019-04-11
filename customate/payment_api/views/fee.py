from rest_framework.permissions import AllowAny
from payment_api.serializers import FeeGroupSerializer


from payment_api.views import (
    InclusionFiler,
    QueryParameterValidationFilter,
    OrderingFilter,
    SearchFilter,
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
        SearchFilter
    )

    class Meta:
        include_resources = ['fees']


class FeeGroupRelationshipView(RelationshipView):
    pass
