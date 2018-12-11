from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles
from rest_framework.utils import formatting

from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from pygments import highlight
from django.utils.translation import gettext_lazy as _
from core.models import Model

# LEXERS = [item for item in get_all_lexers() if item[1]]
# LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
# STYLE_CHOICES = sorted((item, item) for item in get_all_styles())

# Create your models here.


class Address(Model):
    # user = models.ForeignKey(User, related_name='address', on_delete=models.CASCADE)
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
    COMPANY_TYPES = (
        ('PUBLIC LIMITED COMPANY (PLC)', 'public_limited'),
        ('PRIVATE COMPANY LIMITED BY SHARES (LTD)', 'private_limited_by_shares'),
        ('COMPANY LIMITED BY GUARANTEE', 'limited_by_guarantee'),
        ('UNLIMITED COMPANY (UNLTD)', 'unlimited'),
        ('LIMITED LIABILITY PARTNERSHIP (LLP)', 'limited_liability_partnership'),
        ('COMMUNITY INTEREST COMPANY', 'community_interest'),
        ('INDUSTRIAL AND PROVIDENT SOCIETY (IPS)', 'industrial_provident_society'),
        ('ROYAL CHARTER (RC)', 'royal_charter'),
    )
    # account = models.ForeignKey(Account, related_name='account', on_delete=models.CASCADE, null=True)

    is_active = models.BooleanField(
        _('active'),
        default=False,
        help_text=_(
            'Designates whether this company should be treated as active. '
            'Unselect this instead of deleting companies.'
        ),
    )
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True
    )

    company_type = models.CharField(choices=COMPANY_TYPES, max_length=30, blank=True)
    registration_business_name = models.CharField(max_length=50, blank=True)
    registration_number = models.CharField(max_length=8, blank=True)
    is_private = models.BooleanField(
        _('private'),
        default=True,
        help_text=_(
            'Designates whether this company has only owner. '
            'Unselect this to add ability adding shareholders.'
        ),
    )

    def __str__(self):
        return "%s the business address" % self.registration_business_name


class Account(Model):
    # user = models.ForeignKey(User, related_name='account', on_delete=models.CASCADE)
    COLOR_CHOICES = (
        ('Personal', 'personal'),
        ('Business', 'business')
    )
    company = models.OneToOneField(
        Company,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True,
        related_name='account'
    )
    account_type = models.CharField(max_length=10, choices=COLOR_CHOICES, default='Personal')
    position = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return "%s the account" % self.account_type


class Shareholder(Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='shareholders')
    first_name = models.CharField(_('first name'), max_length=30)
    last_name = models.CharField(_('last name'), max_length=150)
    birth_date = models.DateField(_('day of birth'))
    country_of_residence = models.DateField(_('country of residence'))
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this shareholder should be treated as active. '
            'Unselect this instead of deleting shareholder.'
        ),
    )

    def __str__(self):
        return "%s the business address" % self.last_name

#
# class Snippet(Model):
#     created = models.DateTimeField(auto_now_add=True)
#     title = models.CharField(max_length=100, blank=True, default='')
#     code = models.TextField()
#     linenos = models.BooleanField(default=False)
#     language = models.CharField(choices=LANGUAGE_CHOICES, default='python', max_length=100)
#     style = models.CharField(choices=STYLE_CHOICES, default='friendly', max_length=100)
#     owner = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='snippets', on_delete=models.CASCADE)
#     highlighted = models.TextField()
#
#     def save(self, *args, **kwargs):
#         """
#         Use the `pygments` library to create a highlighted HTML
#         representation of the code snippet.
#         """
#         lexer = get_lexer_by_name(self.language)
#         linenos = 'table' if self.linenos else False
#         options = {'title': self.title} if self.title else {}
#         formatter = HtmlFormatter(style=self.style, linenos=linenos,
#                                   full=True, **options)
#         self.highlighted = highlight(self.code, lexer, formatter)
#         super(Snippet, self).save(*args, **kwargs)
#
#     class Meta:
#         ordering = ('created',)
