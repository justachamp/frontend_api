from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import Model
from enumfields import EnumField
from frontend_api.fields import AccountType, CompanyType

from django.db import models



class Address(Model):
    address = models.CharField(max_length=250)
    country = models.CharField(max_length=50)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    locality = models.CharField(max_length=50)
    postcode = models.CharField(max_length=20)

    def __str__(self):
        return "%s the address" % self.address


class Company(Model):
    company_type = EnumField(CompanyType, max_length=30, blank=True, null=True)
    registration_business_name = models.CharField(max_length=50, blank=True)
    registration_number = models.CharField(max_length=8, blank=True)
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
        return "%s the business address" % self.registration_business_name


class Account(Model):

    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True,
        related_name='account'
    )
    account_type = EnumField(AccountType, max_length=10, default=AccountType.personal)
    position = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return "%s the account" % self.account_type


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
