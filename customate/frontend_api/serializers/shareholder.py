
from rest_framework_json_api.serializers import HyperlinkedModelSerializer

from frontend_api.models import (
    Shareholder,
    Company
)

from ..serializers import (
    ResourceRelatedField
)

import logging
logger = logging.getLogger(__name__)

class ShareholderSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'company': 'frontend_api.serializers.CompanySerializer',
    }

    included_serializers = {
        'company': 'frontend_api.serializers.CompanySerializer',
    }

    company = ResourceRelatedField(
        many=False,
        queryset=Company.objects,
        related_link_view_name='shareholder-related',
        related_link_url_kwarg='pk',
        self_link_view_name='shareholder-relationships',
        required=False
    )

    class Meta:
        model = Shareholder
        fields = ('url', 'company', 'is_active', 'first_name', 'last_name', 'birth_date', 'country_of_residence')