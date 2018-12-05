from django.conf import settings
import boto3
from django.contrib.auth import get_user_model
from authentication.cognito.core import constants
from authentication.cognito import utils
# import the logging library
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)


class CognitoException(Exception):
    def __init__(self, message, status):
        super(CognitoException, self).__init__(message)

        self.status = status

    @staticmethod
    def create_from_exception(ex):
        return CognitoException(ex.response['Error']['Message'], ex.response['ResponseMetadata']['HTTPStatusCode'])


class Identity:
    client = boto3.client('cognito-idp', aws_access_key_id=settings.AWS_ACCESS_KEY,
                          aws_secret_access_key=settings.AWS_SECRET_KEY, region_name=settings.AWS_REGION)

    user_class = get_user_model()

    def sign_up(self, username, password, user_attributes, validation_data=None):
        try:
            logger.error(username)
            logger.error(password)
            logger.error(user_attributes)
            secret_hash = utils.get_cognito_secret_hash(username)
            params = {"ClientId": constants.CLIENT_ID,
                      "Username": username, "Password": password,
                      "UserAttributes": user_attributes}

            if validation_data:
                params['ValidationData'] = validation_data

            if secret_hash:
                params['SecretHash'] = secret_hash

            user_params = utils.cognito_to_dict(user_attributes, settings.COGNITO_ATTR_MAPPING)
            cognito_user = self.client.sign_up(**params)
            logger.error(f'cognito user {cognito_user}')
            logger.error(f'user_params {user_params}')
            user = self.user_class.objects.create(
                username=username, email=username, cognito_id=cognito_user['UserSub']
                # first_name=user_params.get('given_name'), last_name=user_params.get('family_name')
            )

            user.save()
            return cognito_user

        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)


    def confirm_sign_up(self, username, confirmation_code, force_alias_creation):
        try:
            secret_hash = utils.get_cognito_secret_hash(username)

            params = {
                'ClientId': constants.CLIENT_ID,
                'Username': username,
                'ForceAliasCreation': force_alias_creation,
                'ConfirmationCode': confirmation_code
            }

            if secret_hash:
                params['SecretHash'] = secret_hash

            return self.client.confirm_sign_up(**params)
        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def initiate_auth(self, username, auth_flow, password=None, refresh_token=None):
        auth_parameters = {}
        secret_hash = utils.get_cognito_secret_hash(auth_parameters.get('USERNAME'))
        if secret_hash:
            auth_parameters['SECRET_HASH'] = secret_hash

        if auth_flow == constants.USER_PASSWORD_FLOW:
            auth_parameters['USERNAME'] = username
            auth_parameters['PASSWORD'] = password
        elif auth_flow == constants.REFRESH_TOKEN_AUTH_FLOW or auth_flow == constants.REFRESH_TOKEN_FLOW:
            if refresh_token is None:
                raise Exception("To use the refresh token flow you must provide a refresh token")
            else:
                auth_parameters['REFRESH_TOKEN'] = refresh_token
        else:
            raise Exception("Provided auth flow is not supported")

        try:

            return self.client.initiate_auth(AuthFlow=auth_flow, ClientId=constants.CLIENT_ID,
                                            AuthParameters=auth_parameters)

        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def refresh_session(self, username, auth_flow, refresh_token=None):
        auth_parameters = {}
        secret_hash = utils.get_cognito_secret_hash(auth_parameters.get('USERNAME'))
        if secret_hash:
            auth_parameters['USERNAME'] = username
            auth_parameters['SECRET_HASH'] = secret_hash

        if auth_flow == constants.REFRESH_TOKEN_AUTH_FLOW or auth_flow == constants.REFRESH_TOKEN_FLOW:
            if refresh_token is None:
                raise Exception("To use the refresh token flow you must provide a refresh token")
            else:
                auth_parameters['REFRESH_TOKEN'] = refresh_token
        else:
            raise Exception("Provided auth flow is not supported")

        try:

            return self.client.initiate_auth(AuthFlow=auth_flow, ClientId=constants.CLIENT_ID,
                                            AuthParameters=auth_parameters)

        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def sign_out(self, access_token):
        try:
            return self.client.global_sign_out(AccessToken=access_token)
        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def respond_to_auth_challenge(self):
        pass

    def forgot_password(self, username):
        secret_hash = utils.get_cognito_secret_hash(username)

        params = {
            'ClientId': constants.CLIENT_ID,
            'Username': username,
        }

        if secret_hash:
            params['SecretHash'] = secret_hash

        try:
            return self.client.forgot_password(**params)
        except constants.AWS_EXCEPTIONS as ex:
            raise CognitoException.create_from_exception(ex)

    def confirm_forgot_password(self, username, code, new_password):
        secret_hash = utils.get_cognito_secret_hash(username)

        params = {
            'ClientId': constants.CLIENT_ID,
            'Username': username,
            'Password': new_password,
            'ConfirmationCode': code
        }

        if secret_hash:
            params['SecretHash'] = secret_hash

        try:
            return self.client.confirm_forgot_password(**params)
        except constants.AWS_EXCEPTIONS as ex:
            raise CognitoException.create_from_exception(ex)

    def admin_get_user(self):
        pass

    def admin_disable_user(self):
        pass

    def admin_delete_user(self):
        pass

    def admin_confirm_sign_up(self):
        pass

    def admin_create_user(self):
        pass

    def admin_update_user_attributes(self):
        pass

    def resend_confirmation_code(self):
        pass

    def admin_list_users(self):
        pass






