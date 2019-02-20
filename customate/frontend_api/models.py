from django.db import models, transaction
from django.utils.translation import gettext_lazy as _

from core.models import Model, Address
from django.contrib.auth import get_user_model
from enumfields import EnumField
from frontend_api.fields import AccountType, CompanyType

from django.db import models

from polymorphic.models import PolymorphicModel


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


class Account(PolymorphicModel, Model):
    user = models.OneToOneField(
        get_user_model(),
        on_delete=models.CASCADE,
        unique=True,
        blank=False
    )


class UserAccount(Account):
    account_type = EnumField(AccountType, max_length=10, default=AccountType.personal)
    position = models.CharField(max_length=50, blank=True, null=True)

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True,
        related_name='account'
    )

    class JSONAPIMeta:
        resource_name = "UserAccount"

    class Meta:
        permissions = (
            ('owner_access', 'Account owner'),
            ('owner_account_access', 'Owner account access'),
            ('owner_group_account_access', 'Owner group account access'),
            ('sub_user_account_access', 'Sud user account access'),
            ('sub_user_group_account_access', 'Sud user group account access'),
            ('manage_sub_user', 'Manage sub-users'),
            ('manage_funding_sources', 'Manage funding sources'),
            ('manage_unload_accounts', 'Manage unload accounts'),
            ('manage_contract', 'Manage contract'),
        )

    def __str__(self):
        return "Owner account"


class AdminUserAccount(Account):

    class Meta:
        permissions = (
            ('admin_account_access', 'Admin account access'),
            ('admin_group_account_access', 'Admin group account access'),
            ('manage_admin_user', 'Manage admins'),
            ('manage_tax', 'Manage tax'),
            ('manage_fee', 'Manage fee'),
            ('login_as_user', 'Login as user')
        )

    def __str__(self):
        return "Admin account"


class SubUserAccount(Account):
    owner_account = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="sub_user_accounts")

    def __str__(self):
        return "Sub user account"


    # class JSONAPIMeta:
    #     resource_name = "SubUserAccount"


class SubUserPermission(Model):
    account = models.OneToOneField(SubUserAccount, on_delete=models.CASCADE, related_name="permission")
    manage_sub_user = models.BooleanField(_('manage sub users'), default=False)
    manage_funding_sources = models.BooleanField(_('manage funding sources'), default=False)
    manage_unload_accounts = models.BooleanField(_('manage unload accounts'), default=False)
    manage_contract = models.BooleanField(_('create contract'), default=False)

    @transaction.atomic
    def save(self, *args, **kwargs):
        from frontend_api.utils import sync_sub_user_permissions
        sync_sub_user_permissions(self)
        return super().save(*args, **kwargs)


    def __str__(self):
        return "Sub user permission"


class AdminUserPermission(Model):
    account = models.OneToOneField(AdminUserAccount, on_delete=models.CASCADE, related_name="permission")
    manage_admin_user = models.BooleanField(_('manage admins'), default=False)
    manage_tax = models.BooleanField(_('manage tax'), default=False)
    manage_fee = models.BooleanField(_('manage fee'), default=False)
    can_login_as_user = models.BooleanField(_('can login'), default=False)

    @transaction.atomic
    def save(self, *args, **kwargs):
        from frontend_api.utils import sync_admin_user_permissions
        sync_admin_user_permissions(self)
        return super().save(*args, **kwargs)

    def __str__(self):
        return "Admin user permission"


class Tax(Model):
    title = models.CharField(max_length=1, blank=False)
    percent = models.DecimalField(max_digits=2, decimal_places=2)
    isDefault = models.BooleanField(_('is default'), default=False)
    taxIban = models.CharField(max_length=1, blank=True)
    feeIban = models.CharField(max_length=1, blank=True)
    createionDate = models.DateField(_('creation date'))

    def __str__(self):
        return "Tax"


class UserTax(Model):
    tax = models.ForeignKey(Tax, on_delete=models.CASCADE, related_name='users')
    user = models.ForeignKey(UserAccount, on_delete=models.CASCADE, related_name="user_taxes")

    def __str__(self):
        return "User Tax"


class FeeGroup(Model):
    title = models.CharField(max_length=1, blank=False)
    isDefault = models.BooleanField(_('is default'), default=False)
    createionDate = models.DateField(_('creation date'))

    def __str__(self):
        return "Fee Group"


class Fee(Model):
    feeGroup = models.ForeignKey(FeeGroup, on_delete=models.CASCADE, related_name='fee_groups')
    min = models.IntegerField(blank=True)
    max = models.IntegerField(blank=True)
    percent = models.DecimalField(max_digits=2, decimal_places=2)
    fixedValue = models.BigIntegerField(blank=True)
    type
    operation

    def __str__(self):
        return "Fee"


class UserFee(Model):
    user = models.OneToOneField(AdminUserAccount, on_delete=models.CASCADE, related_name="user_fees")
    feeGroup = models.ForeignKey(FeeGroup, on_delete=models.CASCADE, related_name='fee_groups')

    def __str__(self):
        return "User Fee"





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
