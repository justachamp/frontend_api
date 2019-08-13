import datetime
from dataclasses import dataclass
from uuid import UUID

from enumfields import EnumField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import JSONField
from django.core.serializers.json import DjangoJSONEncoder
from django.contrib.auth import get_user_model
from core.models import Model, Address
from core.fields import Currency, PaymentScenario
from frontend_api.fields import AccountType, CompanyType

from polymorphic.models import PolymorphicModel

GBG_IDENTITY_VALID_DAYS = 90
GBG_SUCCESS_STATUS = 'Pass'
GBG_ALLOWED_VERIFICATION_COUNT = 3


class Company(Model):
    company_type = EnumField(CompanyType, max_length=30, blank=True, null=True)
    registration_business_name = models.CharField(max_length=50, blank=True)
    registration_number = models.CharField(max_length=8, blank=True)
    vat_number = models.CharField(max_length=12, blank=True)
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True
    )
    is_private = models.BooleanField(
        _('private'),
        default=True,
        help_text=_(
            'Designates whether this company has only owner. '
            'Unselect this to add ability adding shareholders.'
        ),
    )

    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this shareholder should be treated as active. '
            'Unselect this instead of deleting it.'
        ),
    )

    def __str__(self):
        return "%s the company" % self.registration_business_name


def default_account_data_dict():
    return {'version': 1, 'gbg': {}}


class Account(PolymorphicModel, Model):
    verification_status = models.fields.CharField(max_length=100, blank=True, default='Fail')
    data = JSONField(encoder=DjangoJSONEncoder, default=default_account_data_dict)
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        unique=True,
        blank=False
    )

    @property
    def gbg(self):
        data = self.data
        gbg = data.get('gbg', None)
        if not gbg:
            gbg = data['gbg'] = {}
        return gbg

    @gbg.setter
    def gbg(self, gbg):
        self.data['gbg'] = gbg

    @property
    def country_fields(self):
        country_fields = self.gbg.get('country_fields', {})
        return country_fields

    @country_fields.setter
    def country_fields(self, country_fields):
        gbg = self.gbg
        gbg['country_fields'] = country_fields

    @property
    def gbg_authentication_identity(self):
        identity = None
        data = self.data
        gbg = data.get('gbg', None)
        if gbg and gbg.get('id'):
            last_date = datetime.datetime.strptime(gbg.get('date'), '%Y-%m-%dT%H:%M:%S.%f')
            now_date = datetime.datetime.utcnow()
            delta = now_date - last_date
            if delta.days > GBG_IDENTITY_VALID_DAYS:
                identity = gbg.get('id')
        return identity

    @gbg_authentication_identity.setter
    def gbg_authentication_identity(self, authentication_id):
        gbg = self.gbg
        previous_id = self.gbg.get('id', None)
        if authentication_id:
            if authentication_id != previous_id:
                gbg['id'] = authentication_id
                gbg['date'] = datetime.datetime.utcnow()
                gbg['authentication_count'] = gbg.get('authentication_count', 0)

    @property
    def gbg_authentication_count(self):
        return self.gbg.get('authentication_count', 0)

    @gbg_authentication_count.setter
    def gbg_authentication_count(self, count):
        self.gbg['authentication_count'] = count

    @property
    def is_verified(self):
        return self.verification_status == GBG_SUCCESS_STATUS

    @property
    def possible_to_verify(self):
        return self.gbg_authentication_count < GBG_ALLOWED_VERIFICATION_COUNT

    @property
    def can_be_verified(self):
        return not self.is_verified and self.possible_to_verify


class UserAccount(Account):
    account_type = EnumField(AccountType, max_length=10, default=AccountType.personal)
    position = models.CharField(max_length=50, blank=True, null=True)
    payment_account_id = models.UUIDField(null=True, unique=True)

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True,
        related_name='account'
    )

    def __init__(self, *args, **kwargs):
        self._payment_account = None
        super().__init__(*args, **kwargs)

    @property
    def payment_account(self):
        return self._payment_account

    @payment_account.setter
    def payment_account(self, payment_account):
        self._payment_account = payment_account

    class JSONAPIMeta:
        resource_name = "UserAccount"

    def __str__(self):
        return "Owner account"


class AdminUserAccount(Account):

    def __str__(self):
        return "Admin account"


class SubUserAccount(Account):
    owner_account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="sub_user_accounts")

    def __str__(self):
        return "Sub user account"


class SubUserPermission(Model):
    account = models.OneToOneField(SubUserAccount, on_delete=models.CASCADE, related_name="permission")
    load_funds = models.BooleanField(_('load_funds'), default=False)
    manage_funding_sources = models.BooleanField(_('manage funding sources'), default=False)
    manage_payees = models.BooleanField(_('manage_payees'), default=False)
    manage_schedules = models.BooleanField(_('manage schedules'), default=False)

    def __str__(self):
        return "Sub user permission"


class AdminUserPermission(Model):
    account = models.OneToOneField(AdminUserAccount, on_delete=models.CASCADE, related_name="permission")
    manage_tax = models.BooleanField(_('manage tax'), default=False)
    manage_fee = models.BooleanField(_('manage fee'), default=False)

    def __str__(self):
        return "Admin user permission"


class Shareholder(Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='shareholders')
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=150)
    birth_date = models.DateField(_('day of birth'))
    country_of_residence = models.CharField(_('country of residence'), max_length=30)
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this shareholder should be treated as active. '
            'Unselect this instead of deleting id.'
        ),
    )

    def __str__(self):
        return "%s the shareholder" % self.last_name


@dataclass
class PaymentDetails:
    user_id: UUID
    payment_account_id: UUID
    schedule_id: UUID
    currency: Currency
    amount: int
    description: str
    payee_id: UUID
    funding_source_id: UUID


from frontend_api.models.schedule import PayeeDetails, FundingSourceDetails, Schedule

__all__ = [
    Company,
    Shareholder,
    Account,
    UserAccount,
    AdminUserAccount,
    SubUserAccount,
    SubUserPermission,
    AdminUserPermission,

    # Schedules
    Schedule,
    PayeeDetails,
    FundingSourceDetails
]
