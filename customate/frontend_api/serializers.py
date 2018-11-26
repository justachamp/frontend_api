from django.contrib.auth.models import Group
from rest_framework_json_api import serializers
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework_json_api.relations import ResourceRelatedField

from core.models import User
from frontend_api.models import Address

# from rest_framework import serializers
# from frontend_api.models import Snippet, LANGUAGE_CHOICES, STYLE_CHOICES



# erializers.HyperlinkedModelSerializer
# Polymorphic
class UserSerializer(serializers.HyperlinkedModelSerializer):
    # snippets = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())

    related_serializers = {
        'address': 'frontend_api.serializers.AddressSerializer'
    }

    address = ResourceRelatedField(
        many=True,
        queryset=Address.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',

    )



# class UserSerializer(serializers.HyperlinkedModelSerializer):
#     snippets = serializers.HyperlinkedRelatedField(many=True, view_name='api-root', read_only=True)
#     snippets = ResourceRelatedField(
#         queryset=Snippet.objects,
#         many=True,
#         # related_link_view_name='user-snippet-list',
#         related_link_url_kwarg='user_pk',
#         # self_link_view_name='snippet-list'
#     )

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'groups', 'address')


class AddressSerializer(serializers.ModelSerializer):
    user = serializers.ReadOnlyField(source='user.username')

    class Meta:
        model = Address
        fields = ('address', 'country', 'adress_line_1', 'adress_line_2', 'city', 'locality', 'postcode', 'user')


class GroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ('url', 'name')


# class SnippetSerializer(serializers.ModelSerializer):
#     owner = serializers.ReadOnlyField(source='owner.username')
#
#     class Meta:
#         model = Snippet
#         fields = ('title', 'code', 'linenos', 'language', 'style', 'owner')


# class SnippetSerializer(serializers.HyperlinkedModelSerializer):
#     owner = serializers.ReadOnlyField(source='owner.username')
#     # highlight = HyperlinkedIdentityField(view_name='snippet-highlight', format='html')
#
#     class Meta:
#         model = Snippet
#         fields = ('url', 'id', 'owner',
#                   'title', 'code', 'linenos', 'language', 'style')