
from rest_framework_json_api.serializers import HyperlinkedModelSerializer

from core.models import User, Address
from frontend_api.models import Company

from ..serializers import ResourceRelatedField

import logging
logger = logging.getLogger(__name__)


class UserAddressSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer'
    }

    included_serializers = {
        'user': 'frontend_api.serializers.UserSerializer'
    }

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False

    )

    class Meta:
        model = Address
        fields = ('url', 'address', 'country', 'address_line_1', 'address_line_2', 'address_line_3',
                  'city', 'locality', 'postcode', 'user')


class AddressSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer'
    }

    included_serializers = {
        'user': 'frontend_api.serializers.UserSerializer',
        'company': 'frontend_api.serializers.CompanySerializer'
    }

    user = ResourceRelatedField(
        many=False,
        queryset=User.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False

    )

    company = ResourceRelatedField(
        many=False,
        queryset=Company.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False

    )

    class Meta:
        model = Address
        fields = ('url', 'address', 'country', 'address_line_1', 'address_line_2', 'address_line_3',
                  'city', 'locality', 'postcode', 'user', 'company')


class CompanyAddressSerializer(HyperlinkedModelSerializer):

    related_serializers = {
        'company': 'frontend_api.serializers.CompanySerializer'
    }

    included_serializers = {
        'company': 'frontend_api.serializers.CompanySerializer'
    }

    company = ResourceRelatedField(
        many=False,
        queryset=Company.objects,
        related_link_view_name='address-related',
        related_link_url_kwarg='pk',
        self_link_view_name='address-relationships',
        required=False
    )

    class Meta:
        model = Address
        fields = ('url', 'address', 'country', 'address_line_1', 'address_line_2', 'address_line_3',
                  'city', 'locality', 'postcode', 'company')
