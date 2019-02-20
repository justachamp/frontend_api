from rest_framework_json_api.views import viewsets
from frontend_api.serializers import DatasetSerializer

from rest_framework.decorators import action
from rest_framework import response
from core.fields import UserTitle, Gender, Country, CountryDialCode

from customate.settings import COUNTRIES_AVAILABLE

# import the logging library
import logging
import uuid

# Get an instance of a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DatasetView(viewsets.ViewSet):

    @action(methods=['GET'], detail=False)
    def all(self, request):
        serializer = DatasetSerializer(data={
            "titles": [title.label for title in UserTitle],
            "genders": [gender.label for gender in Gender],
            "countriesAvailable": [{
                'iso': country.value,
                'name': country.label,
                'phoneCode': CountryDialCode[country.value].value
            } for country in Country if (country.value in COUNTRIES_AVAILABLE)],
            "countriesAll": [{
                'iso': country.value,
                'name': country.label,
                'phoneCode': CountryDialCode[country.value].value
            } for country in Country],
        })
        serializer.is_valid()
        return response.Response(serializer.data)
