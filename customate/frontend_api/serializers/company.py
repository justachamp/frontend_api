
from rest_framework_json_api.serializers import HyperlinkedModelSerializer
from core.models import Address

from frontend_api.models import (
    Shareholder,
    Company,
    UserAccount
)

from frontend_api.fields import CompanyType

from ..serializers import (
    EnumField,
    CharField,
    ResourceRelatedField
)

import logging
logger = logging.getLogger(__name__)


class CompanySerializer(HyperlinkedModelSerializer):

    registration_number = CharField(min_length=6, max_length=8, allow_blank=True)

    related_serializers = {
        'account': 'frontend_api.serializers.UserAccountSerializer',
        'address': 'frontend_api.serializers.CompanyAddressSerializer',
        'shareholders': 'frontend_api.serializers.ShareholderSerializer'
    }

    included_serializers = {
        'account': 'frontend_api.serializers.UserAccountSerializer',
        'address': 'frontend_api.serializers.CompanyAddressSerializer',
        'shareholders': 'frontend_api.serializers.ShareholderSerializer'
    }

    account = ResourceRelatedField(
        many=False,
        queryset=UserAccount.objects,
        related_link_view_name='company-related',
        related_link_url_kwarg='pk',
        self_link_view_name='company-relationships',
        required=False
    )

    shareholders = ResourceRelatedField(
        many=True,
        queryset=Shareholder.objects,
        related_link_view_name='company-related',
        related_link_url_kwarg='pk',
        self_link_view_name='company-relationships',
        required=False
    )

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='company-related',
        related_link_url_kwarg='pk',
        self_link_view_name='company-relationships',
        required=False
    )

    company_type = EnumField(enum=CompanyType)

    class Meta:
        model = Company
        fields = ('url', 'company_type', 'is_active', 'registration_business_name', 'vat_number', 'registration_number',
                  'is_private', 'shareholders', 'account', 'address')