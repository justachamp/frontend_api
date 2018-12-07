from django.contrib.auth.models import Group
from rest_framework_json_api import serializers
from rest_framework.serializers import HyperlinkedIdentityField
from rest_framework_json_api.relations import ResourceRelatedField

from core.models import User
from frontend_api.models import Address, Account
import logging
logger = logging.getLogger(__name__)



class UserSerializer(serializers.HyperlinkedModelSerializer):
    # snippets = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())

    related_serializers = {
        'address': 'frontend_api.serializers.AddressSerializer',
        'account': 'frontend_api.serializers.AccountSerializer'
    }

    address = ResourceRelatedField(
        many=False,
        queryset=Address.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False

    )

    account = ResourceRelatedField(
        many=False,
        queryset=Account.objects,
        related_link_view_name='user-related',
        related_link_url_kwarg='pk',
        self_link_view_name='user-relationships',
        required=False

    )

    # def update(self, validated_data, test):
    #     logger.error(f'validated_data {validated_data} {test}')

    # def create(self, validated_data):
    #     logger.error(f'validated_data {validated_data}')

        # tracks_data = validated_data.pop('tracks')
        # album = Album.objects.create(**validated_data)
        # for track_data in tracks_data:
        #     Track.objects.create(album=album, **track_data)
        # return album



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
        fields = ('url', 'username', 'first_name', 'last_name', 'middle_name', 'phone_number', 'birth_date', 'last_name', 'email', 'groups', 'address', 'account')



class AddressSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Address
        fields = ('address', 'country', 'address_line_1', 'address_line_2', 'city', 'locality', 'postcode', 'user')


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    user = serializers.ReadOnlyField(source='user.id')

    class Meta:
        model = Account
        fields = ('account_type', 'user')


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