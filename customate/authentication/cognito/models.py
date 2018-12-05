from django.db import models

# Create your models here.


class Identity(object):
    def __init__(self, **kwargs):
        for field in ('id', 'preferred_username', 'user_attributes', 'id_token', 'access_token', 'refresh_token'):
            setattr(self, field, kwargs.get(field, None))

        self.pk = getattr(self, 'id')
