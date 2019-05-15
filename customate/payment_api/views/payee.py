from rest_framework.permissions import AllowAny

from payment_api.serializers import PayeeSerializer


from payment_api.views import (
    InclusionFilter,
    OrderingFilter,
    SearchFilter,
    ResourceFilterBackend,
    ResourceRelationshipView,
    ResourceViewSet
)


class PayeeViewSet(ResourceViewSet):
    resource_name = 'payees'
    serializer_class = PayeeSerializer
    permission_classes = (AllowAny,)

    filter_backends = (
        OrderingFilter,
        InclusionFilter,
        ResourceFilterBackend,
        SearchFilter
    )

    def check_payment_account_id(self, filters, key, value):
        user = self.request.user
        if not user.is_anonymous and user.is_owner and user.account.payment_account_id:
            return user.account.payment_account_id
        else:
            self.get_queryset().set_empty_response()

    filterset_fields = {
        'type': ('exact',),
        'currency': ('exact',),
        'active': ('exact',),
        'account__id': ('exact',),
    }

    class Meta:
        filters = [
            {'active__exact': 1},
            {'account__id__exact': {'method': 'check_payment_account_id'}}
        ]
        resource_mapping = [
            {'accounts': {'op': 'map', 'value': 'account'}}
        ]


class PayeeRelationshipView(ResourceRelationshipView):
    serializer_class = PayeeSerializer
    resource_name = 'peyees'
