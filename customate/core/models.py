from django.utils.translation import gettext_lazy as _
from django.contrib.auth.models import AbstractUser
from core.utils import Model
from django.db import models
from frontend_api.models import Account, Address


class User(AbstractUser, Model):
    cognito_id = models.UUIDField(null=True, unique=True)
    email = models.EmailField(_('email address'), unique=True, blank=False)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def get_username(self):
        return self.email

    address = models.OneToOneField(
        Address,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True
    )
    account = models.OneToOneField(
        Account,
        on_delete=models.CASCADE,
        unique=True,
        blank=True,
        null=True
    )







