from django.utils.translation import gettext_lazy as _
from rest_framework_json_api.serializers import HyperlinkedModelSerializer
from core.models import Address

from frontend_api.models import (
    Shareholder,
    Company,
    UserAccount,
    OptionalSchemeURLValidator)

from frontend_api.fields import CompanyType

from frontend_api.serializers import (
    EnumField,
    CharField,
    ResourceRelatedField
)

import logging
logger = logging.getLogger(__name__)


class OptionalSchemeURLField(CharField):
    default_error_messages = {
        'invalid': _('Enter a valid URL.')
    }

    def __init__(self, **kwargs):
        super(OptionalSchemeURLField, self).__init__(**kwargs)
        validator = OptionalSchemeURLValidator(message=self.error_messages['invalid'])
        self.validators.append(validator)


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
    business_website_url = OptionalSchemeURLField()

    class Meta:
        model = Company
        fields = ('url', 'company_type', 'is_active', 'registration_business_name', 'vat_number', 'registration_number',
                  'is_private', 'shareholders', 'account', 'address', 'business_website_url')
