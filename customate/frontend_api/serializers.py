from django.contrib.auth.models import User, Group
from rest_framework_json_api import serializers
# erializers.HyperlinkedModelSerializer
# Polymorphic
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')