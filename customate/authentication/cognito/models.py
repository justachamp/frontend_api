from django.db import models

# Create your models here.

class Entity(object):
    fields = []

    def __init__(self, **kwargs):
        for field in self.fields:
            setattr(self, field, kwargs.get(field, None))

        self.pk = getattr(self, 'id')


class Identity(object):
    def __init__(self, **kwargs):
        for field in ('id', 'preferred_username', 'user_attributes', 'id_token', 'access_token', 'refresh_token',
                      'account_type', 'user'):
            setattr(self, field, kwargs.get(field, None))

        self.pk = getattr(self, 'id')


class Verification(Entity):
    fields = ('id', 'attribute_name', 'destination')
