from rest_framework.permissions import AllowAny
from payment_api.serializers import TaxSerializer

from payment_api.views import (
    RelationshipView,
    ResourceViewSet
)


class TaxViewSet(ResourceViewSet):
    resource_name = 'taxes'
    serializer_class = TaxSerializer
    permission_classes = (AllowAny,)


class TaxRelationshipView(RelationshipView):
    pass
