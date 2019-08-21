import uuid
from datetime import date

from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from django.db import models

from phonenumber_field.modelfields import PhoneNumberField
from enumfields import EnumField

from core.fields import UserStatus, UserRole, UserTitle, Gender, Country

USER_MIN_AGE = 18


class Model(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Address(Model):
    address = models.CharField(max_length=250, blank=True)
    country = EnumField(Country, max_length=2, blank=True, null=True)
    address_line_1 = models.CharField(max_length=200, blank=True)
    address_line_2 = models.CharField(max_length=200, blank=True)
    address_line_3 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=50, blank=True)
    locality = models.CharField(max_length=50, blank=True)
    postcode = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return "%s" % self.address


class User(AbstractUser, Model):
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    cognito_id = models.UUIDField(null=True, unique=True)
    email = models.EmailField(_('email address'), unique=True, blank=False)
    status = EnumField(UserStatus, max_length=10, default=UserStatus.active)
    role = EnumField(UserRole, max_length=10, null=True)
    middle_name = models.CharField(_('first name'), max_length=30, blank=True)
    birth_date = models.DateField(_('day of birth'), blank=True, null=True)  # type: date
    phone_number = PhoneNumberField(blank=True)

    title = EnumField(UserTitle, max_length=10, blank=True, null=True)
    gender = EnumField(Gender, max_length=10, blank=True, null=True)
    country_of_birth = EnumField(Country, max_length=2, blank=True, null=True)
    mother_maiden_name = models.CharField(_('mother maiden name'), max_length=100, blank=True, null=True)
    passport_number = models.CharField(_('passport number'), max_length=50, blank=True)
    passport_date_expiry = models.DateField(_('day of birth'), blank=True, null=True)
    passport_country_origin = EnumField(Country, max_length=2, blank=True, null=True)

    phone_number_verified = models.BooleanField(
        _('phone number verified'),
        default=False,
        help_text=_(
            'Designates whether this company has only owner. '
            'Unselect this to add ability to add shareholders.'
        ),
    )

    email_verified = models.BooleanField(
        _('phone number verified'),
        default=False,
        help_text=_(
            'Designates whether this company has only owner. '
            'Unselect this to add ability to add shareholders.'
        ),
    )
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True
    )

    def __str__(self):
        return "%s (cognito_id=%s, role=%r)" % (self.email, self.cognito_id, self.role)

    @property
    def is_owner(self):
        return self.role == UserRole.owner

    @property
    def is_subuser(self):
        return self.role == UserRole.sub_user

    @property
    def is_admin(self):
        return self.role == UserRole.admin

    @property
    def is_verified(self):
        return self.contact_verified and self.age_verified

    @property
    def is_owner_account_verified(self):
        #TODO: where do we get self.account from?????
        return self.is_subuser and self.account.is_owner_account_verified

    @property
    def contact_verified(self):
        return self.email_verified and self.phone_number_verified

    @property
    def age(self) -> int:
        age = None
        today = date.today()
        birth_date = self.birth_date
        if birth_date:
            age = (today.year - birth_date.year) - int((today.month, today.day) < (birth_date.month, birth_date.day))
        return age

    @property
    def age_verified(self) -> bool:
        return self.birth_date and self.age >= USER_MIN_AGE

    def get_username(self):
        return self.email
