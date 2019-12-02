import logging
from rest_framework import serializers
from rest_framework.fields import DateField, IntegerField, BooleanField, CharField

logger = logging.getLogger(__name__)


# class CatSerializer(serializers.Serializer):
class CatSerializer(serializers.Serializer):
    """Your data serializer, define your fields here."""
    comments = serializers.IntegerField()
    likes = serializers.IntegerField()
    name = CharField(required=True)

    def validate_name(self, value):
        """
        Make sure we avoid duplicate names for the same user.
        :param name:
        :return:
        """
        logger.info("Validating name: %s" % value)
        # return "Formatted {} cat ".format(value)
        return {"cc": value, "o": 1}
