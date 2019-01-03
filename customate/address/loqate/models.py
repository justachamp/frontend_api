from django.db import models

class Entity(object):
    fields = []

    def __init__(self, **kwargs):
        for field in self.fields:
            setattr(self, field, kwargs.get(field, None))

        self.pk = getattr(self, 'id')


class RetrieveAddress(Entity):
    fields = ('id',)

# Create your models here.
