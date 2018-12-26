"""Custom Django authentication backend"""
import abc

from boto3.exceptions import Boto3Error
from botocore.exceptions import ClientError
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils.six import iteritems

# from warrant import Cognito
from .utils import cognito_to_dict


class CognitoUser():

    def get_user_obj(self,username=None,attribute_list=[],metadata={},attr_map={}):
        user_attrs = cognito_to_dict(attribute_list,CognitoUser.COGNITO_ATTR_MAPPING)
        django_fields = [f.name for f in CognitoUser.user_class._meta.get_fields()]
        extra_attrs = {}
        for k, v in user_attrs.items():
            if k not in django_fields:
                extra_attrs.update({k: user_attrs.pop(k, None)})
        if getattr(settings, 'COGNITO_CREATE_UNKNOWN_USERS', True):
            user, created = CognitoUser.user_class.objects.update_or_create(
                username=username,
                defaults=user_attrs)
        else:
            try:
                user = CognitoUser.user_class.objects.get(username=username)
                for k, v in iteritems(user_attrs):
                    setattr(user, k, v)
                user.save()
            except CognitoUser.user_class.DoesNotExist:
                    user = None
        if user:
            for k, v in extra_attrs.items():
                setattr(user, k, v)
        return user


class AbstractCognitoBackend(ModelBackend):
    __metaclass__ = abc.ABCMeta

    UNAUTHORIZED_ERROR_CODE = 'NotAuthorizedException'

    USER_NOT_FOUND_ERROR_CODE = 'UserNotFoundException'

    COGNITO_USER_CLASS = CognitoUser

    @abc.abstractmethod
    def authenticate(self, username=None, password=None):
        """
        Authenticate a Cognito User
        :param username: Cognito username
        :param password: Cognito password
        :return: returns User instance of AUTH_USER_MODEL or None
        """
        cognito_user = CognitoUser(
            settings.COGNITO_USER_POOL_ID,
            settings.COGNITO_APP_CLIENT_ID,
            access_key=getattr(settings, 'AWS_ACCESS_KEY', None),
            secret_key=getattr(settings, 'AWS_SECRET_KEY', None),
            user_pool_region=getattr(settings, 'AWS_REGION', None),
            username=username)
        try:
            cognito_user.authenticate(password)
        except (Boto3Error, ClientError) as e:
            return self.handle_error_response(e)
        user = cognito_user.get_user()
        if user:
            user.access_token = cognito_user.access_token
            user.id_token = cognito_user.id_token
            user.refresh_token = cognito_user.refresh_token

        return user

    def handle_error_response(self, error):
        error_code = error.response['Error']['Code']
        if error_code in [
                AbstractCognitoBackend.UNAUTHORIZED_ERROR_CODE,
                AbstractCognitoBackend.USER_NOT_FOUND_ERROR_CODE
            ]:
            return None
        raise error


class CognitoBackend(AbstractCognitoBackend):
    def authenticate(self, request, username=None, password=None):
        """
        Authenticate a Cognito User and store an access, ID and
        refresh token in the session.
        """
        user = super(CognitoBackend, self).authenticate(
            username=username, password=password)
        if user:
            request.session['ACCESS_TOKEN'] = user.access_token
            request.session['ID_TOKEN'] = user.id_token
            request.session['REFRESH_TOKEN'] = user.refresh_token
            request.session.save()
        return user

class CognitoRestBackend(AbstractCognitoBackend):
    def authenticate(self, request):
        # This is where we will extract information about the incoming access token from the user,
        # and decide whether or not they are authenticated
        logger.error('authenticate AwsRestAuthentication')
        user, access_token, refresh_token = helpers.process_request(request)

        # TODO: Potentially create a mixin for views overriding the .finalise_response method to ensure if we
        # end up with a new access token as part of this process, we are able to set it in the response
        #
        # Need some way of setting a new access token or refresh token in the final response
        return user, access_token


    def authenticate(self, request):
        try:
            access_token = request.META.get('HTTP_ACCESSTOKEN')
            refresh_token = request.META.get('HTTP_REFRESHTOKEN')
            logger.error(f'access_token: {access_token} refresh_token: {refresh_token}')
            if not access_token or not refresh_token:
                # Need to have this to authenticate, error out
                raise Exception("No valid tokens were found in the request")
            else:
                new_access_token, new_refresh_token = validate_token(access_token, refresh_token)

                header, payload = decode_token(access_token)

                try:
                    user = get_user_model().objects.get(username=payload['username'])
                except Exception as ex:
                    if settings.AUTO_CREATE_USER:
                        aws_user = actions.admin_get_user(payload['username'])

                        user_attributes = {k: v for dict in
                                           [{d['Name']: d['Value']} for d in aws_user['UserAttributes']]
                                           for k, v in dict.items()}

                        user = get_user_model().objects.create(username=payload['username'],
                                                               email=user_attributes['email'],
                                                               first_name=user_attributes['given_name'],
                                                               last_name=user_attributes['family_name'])

                        user.save()
                    else:
                        return AnonymousUser, None, None

            return user, new_access_token, new_refresh_token

        except Exception as ex:
            logger.error(ex)
            return AnonymousUser(), None, None