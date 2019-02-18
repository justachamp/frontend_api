from rest_framework.exceptions import ValidationError
from rest_framework.fields import DateField

from rest_framework_json_api.serializers import CharField, PolymorphicModelSerializer

from .mixins import FlexFieldsJsonFieldSerializerMixin
from .fields import ChoiceField, EnumField, ResourceRelatedField, PolymorphicResourceRelatedField
from .account import UserAccountSerializer, SubUserAccountSerializer, AdminUserAccountSerializer
from .user import UserSerializer, SubUserSerializer, AdminUserSerializer
from .address import AddressSerializer, UserAddressSerializer, CompanyAddressSerializer
from .permission import SubUserPermissionSerializer, AdminUserPermissionSerializer


ACCOUNT_ADDITIONAL_FIELDS = {
    'GB': {
        'driver_licence_number': CharField(source='country_fields.driver_licence_number', default=None),
        'driver_licence_postcode': CharField(source='country_fields.driver_licence_postcode', default=None),
        'driver_licence_issue_date': DateField(source='country_fields.driver_licence_issue_date', default=None)
    },
    'IT': {'tax_code': CharField(source='country_fields.tax_code', default=None)},
    'DK': {'id_card_number': CharField(source='country_fields.id_card_number', default=None)},
    'SP': {'tax_id': CharField(source='country_fields.tax_id', default=None)}
}


__all__ = [
    ACCOUNT_ADDITIONAL_FIELDS,
    ValidationError,
    CharField,
    PolymorphicModelSerializer,
    FlexFieldsJsonFieldSerializerMixin,
    ChoiceField,
    EnumField,
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    UserAccountSerializer,
    SubUserAccountSerializer,
    AdminUserAccountSerializer,
    UserSerializer,
    SubUserSerializer,
    AdminUserSerializer,
    AddressSerializer,
    UserAddressSerializer,
    CompanyAddressSerializer,
    SubUserPermissionSerializer,
    AdminUserPermissionSerializer
]