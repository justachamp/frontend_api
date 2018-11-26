import uuid
from django.contrib.auth.models import AbstractUser, Group as BaseGroupModel
from django.db import models



class Model(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4)
    USERNAME_FIELD = 'email'
    class Meta:
        abstract = True

class User(AbstractUser, Model):
    cognito_id = models.UUIDField(null=True, unique=True)










