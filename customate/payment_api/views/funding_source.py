import logging
from rest_framework.permissions import AllowAny
from payment_api.serializers import FundingSourceSerializer

logger = logging.getLogger(__name__)

from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
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
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    filterset_fields = {
        'status': ('exact',),
        'active': ('exact',),
        'account__id': ('exact',),
        'type': ('exact', )
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            #{'type__exact': "CREDIT_CARD"},
            {'account__id__exact': {'method': 'check_payment_account_id'}}
        ]

    def check_payment_account_id(self, filters, key, value):
        logger.debug("filters=%r, key=%r, value=%r" % (filters, key, value))
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()


class FundingSourceRelationshipView(ResourceRelationshipView):
    serializer_class = FundingSourceSerializer
    resource_name = 'funding_sources'
