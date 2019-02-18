
from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer,
)

from frontend_api.services.account import AccountService
from core.models import User, Address

from frontend_api.models import (
    Account,
    Shareholder,
    Company,
    SubUserAccount,
    AdminUserAccount,
    AdminUserPermission,
    SubUserPermission,
    UserAccount
)

from frontend_api.fields import AccountType, CompanyType

from ..serializers import (
    EnumField,
    CharField,
    ResourceRelatedField,
    PolymorphicResourceRelatedField,
    ValidationError,
    FlexFieldsJsonFieldSerializerMixin,
    PolymorphicModelSerializer,
    ACCOUNT_ADDITIONAL_FIELDS)

import logging
logger = logging.getLogger(__name__)
























