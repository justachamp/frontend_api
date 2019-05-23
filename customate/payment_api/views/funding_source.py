import logging
from rest_framework.permissions import AllowAny
from payment_api.serializers import FundingSourceSerializer, UpdateFundingSourceSerializer

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
        'type': ('exact', ),
        'currency': ('exact', 'not_in')
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            #{'type__exact': "CREDIT_CARD"},
            {'account__id__exact': {'method': 'check_payment_account_id'}},
            {'currency__not_in': 'DK'}
        ]

    def get_serializer_class(self):
        return UpdateFundingSourceSerializer if self.request.method == 'PATCH' else FundingSourceSerializer

    def check_payment_account_id(self, filters, key, value):
        logger.debug("filters=%r, key=%r, value=%r" % (filters, key, value))
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()

    def perform_create(self, *args, **kwargs):
        logger.debug("Calling perform_create")
        #param = self.request.query_params.get('ibanGeneralPart')
        #iban = param.strip() if param else None
        #if iban:
        #self.client.request_kwargs = {'params': {'ibanGeneralPart': "BLLLAAAA"}}
        return super().perform_create(*args, **kwargs)


class FundingSourceRelationshipView(ResourceRelationshipView):
    serializer_class = FundingSourceSerializer
    resource_name = 'funding_sources'
