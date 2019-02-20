from rest_framework_json_api import serializers
from django.db import models

from ..serializers import (
    DictField,
    CharField,
    ListField,
)


class Dataset(models.Model):
    managed = False


class DatasetSerializer(serializers.ModelSerializer):
    countriesAvailable = ListField(child=DictField(child=CharField()))
    countriesAll = ListField(child=DictField(child=CharField()))
    titles = ListField(child=CharField())
    genders = ListField(child=CharField())

    class Meta:
        model = Dataset
        fields = ['titles', 'genders', 'countriesAvailable', 'countriesAll']
