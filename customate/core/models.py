from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractBaseUser, AbstractUser
from core.utils import Model
from django.db import models
# from frontend_api.models import Address
from phonenumber_field.modelfields import PhoneNumberField
# from polymorphic.models import PolymorphicModel
from enumfields import EnumField
from core.fields import UserStatus, UserRole


class Address(Model):
    address = models.CharField(max_length=250)
    country = models.CharField(max_length=50)
    address_line_1 = models.CharField(max_length=100)
    address_line_2 = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=50)
    locality = models.CharField(max_length=50)
    postcode = models.CharField(max_length=20)

    verified = models.BooleanField(
        _('address verified'),
        default=False,
        help_text=_(
            'Designates whether this address is verified by GBG.'
        ),
    )

    def __str__(self):
        return "%s the address" % self.address


class User(AbstractUser, Model):
    cognito_id = models.UUIDField(null=True, unique=True)
    email = models.EmailField(_('email address'), unique=True, blank=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    status = EnumField(UserStatus, max_length=10, default=UserStatus.inactive)
    role = EnumField(UserRole, max_length=10, null=True)
    middle_name = models.CharField(_('first name'), max_length=30, blank=True)
    birth_date = models.DateField(_('day of birth'), blank=True, null=True)
    phone_number = PhoneNumberField(blank=True)
    is_verified = models.BooleanField(
        _('user verified'),
        default=False,
        help_text=_(
            'Designates whether this user is verified.'
        ),
    )

    phone_number_verified = models.BooleanField(
        _('phone number verified'),
        default=False,
        help_text=_(
            'Designates whether this company has only owner. '
            'Unselect this to add ability adding shareholders.'
        ),
    )

    email_verified = models.BooleanField(
        _('phone number verified'),
        default=False,
        help_text=_(
            'Designates whether this company has only owner. '
            'Unselect this to add ability adding shareholders.'
        ),
    )
    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True
    )

    @property
    def is_owner(self):
        return self.role == UserRole.owner

    @property
    def is_subuser(self):
        return self.role == UserRole.sub_user

    @property
    def is_admin(self):
        return self.role == UserRole.admin


    def check_verification(self):
        address_verified = self.address and self.address.verified
        contact_verified = self.email_verified and self.phone_number_verified
        self.is_verified = contact_verified and address_verified
        is_changeable = self.status not in (UserStatus.banned, UserStatus.blocked)
        if self.is_verified and is_changeable:
            self.status = UserStatus.active
        elif is_changeable:
            self.status = UserStatus.inactive

    def get_username(self):
        return self.email









