from django.conf import settings
import boto3
from django.contrib.auth import get_user_model
# from frontend_api.models import CustomateUser as User
from authentication.cognito.core import constants
from authentication.cognito import utils

from frontend_api.models import Account, Company, UserAccount
from core.fields import UserRole
from botocore.exceptions import ParamValidationError
# import the logging library
import logging
# Get an instance of a logger
from frontend_api.utils import assign_permissions

logger = logging.getLogger(__name__)
from django.db import transaction
from rest_framework import exceptions, status
from rest_framework_json_api import exceptions
BUSINESS_ACCOUNT = 'business'
BAD_DATA_EXCEPTION = "The required parameters were not passed through in the data dictionary"

COGNITO_EXCEPTIONS = {
    'UserNotFoundException': 'Email address does not exist'
}


class CognitoException(Exception):
    def __init__(self, message, status):
        super(CognitoException, self).__init__(message)

        self.status = status

    @staticmethod
    def create_from_exception(ex):
        msg = COGNITO_EXCEPTIONS.get(ex.response['Error']['Code'], ex.response['Error']['Message'])
        return CognitoException(msg, ex.response['ResponseMetadata']['HTTPStatusCode'])

    @staticmethod
    def create_from_boto_exception(ex):
        raise ex

        # for message in response.data:
        #     errors.append({
        #         'detail': message,
        #         'source': {
        #             'pointer': '/data',
        #         },
        #         'status': encoding.force_text(response.status_code),
        #     })


        # return Exception({'password': 'test', 'username': 'some'})

        # return exceptions.APIException(ex)


class Identity:
    client = boto3.client('cognito-idp', aws_access_key_id=settings.AWS_ACCESS_KEY,
                          aws_secret_access_key=settings.AWS_SECRET_KEY, region_name=settings.AWS_REGION)

    user_class = get_user_model()
    # user_class = User

    @transaction.atomic()
    def sign_up(self, username, password, account_type, user_attributes, validation_data=None):
        try:
            logger.error(username)
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
            with transaction.atomic():

                user = self.user_class.objects.create(
                    username=username,
                    email=username,
                    role=UserRole.owner,
                    cognito_id=cognito_user['UserSub']
                    # first_name=user_params.get('given_name'), last_name=user_params.get('family_name')
                )
                account = UserAccount.objects.create(account_type=account_type, user=user)
                account.save()
                user.save()
                assign_permissions(user)

            return cognito_user

        except ParamValidationError as ex:
            logger.error(f'BOTOCORE_EXCEPTIONS {ex}')
            raise CognitoException.create_from_boto_exception(ex)

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
                'ForceAliasCreation': False, # force_alias_creation,
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

    def verification_code(self, attribute_name, access_token):
        try:
            return self.client.get_user_attribute_verification_code(AttributeName=attribute_name, AccessToken=access_token)
        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def verify_attribute(self, attribute_name, access_token, code):
        try:
            return self.client.verify_user_attribute(AttributeName=attribute_name, AccessToken=access_token, Code=code)
        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    @staticmethod
    def _get_challenge_responses(username, challenge_name, responses):
        secret_hash = utils.get_cognito_secret_hash(username)
        # challenge_hash = f' , {secret_hash}' if secret_hash else ''

        if challenge_name == 'SMS_MFA':
            params = {
                'SMS_MFA_CODE': responses,
                'USERNAME': username
            }
            if secret_hash:
                params['SECRET_HASH'] = secret_hash

            return params
        elif challenge_name == 'NEW_PASSWORD_REQUIRED':
            params = {
                'NEW_PASSWORD': responses,
                'USERNAME': username
            }
            if secret_hash:
                params['SECRET_HASH'] = secret_hash

            return params
        else:
            raise Exception('Unsupported challenge name')

    def respond_to_auth_challenge(self, username, challenge_name, responses, session):
        try:

            responses = self._get_challenge_responses(username, challenge_name, responses)
            params = {"ClientId": constants.CLIENT_ID,
                      "ChallengeName": challenge_name,
                      "Session": session,
                      "ChallengeResponses": responses
                      }

            return self.client.respond_to_auth_challenge(**params)
        except ParamValidationError as ex:
            logger.error(f'BOTOCORE_EXCEPTIONS {ex}')
            raise CognitoException.create_from_boto_exception(ex)

        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

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

    def restore_password(self, username, code, password):
        secret_hash = utils.get_cognito_secret_hash(username)

        params = {
            'ClientId': constants.CLIENT_ID,
            'Username': username,
            'Password': password,
            'ConfirmationCode': code
        }

        if secret_hash:
            params['SecretHash'] = secret_hash

        try:
            data = self.client.confirm_forgot_password(**params)
            return data
        except constants.AWS_EXCEPTIONS as ex:
            raise CognitoException.create_from_exception(ex)

    def admin_get_user(self, username):
        params = {
            'UserPoolId': constants.POOL_ID,
            'Username': username
        }

        try:
            data = self.client.admin_get_user(**params)
            return data
        except constants.AWS_EXCEPTIONS as ex:
            raise CognitoException.create_from_exception(ex)

    def admin_create_user(self, username, user_attributes, password=None, action=None, delivery=None, validation_data=None):
        try:
            logger.error(username)
            logger.error(user_attributes)

            params = {
                'UserPoolId': constants.POOL_ID,
                'Username': username,
                'UserAttributes': user_attributes,
                'TemporaryPassword': password
            }

            if action:
                params['MessageAction'] = action

            if delivery:
                params['DesiredDeliveryMediums'] = delivery

            if validation_data:
                params['ValidationData'] = validation_data

            user_params = utils.cognito_to_dict(user_attributes, settings.COGNITO_ATTR_MAPPING)
            cognito_user = self.client.admin_create_user(**params)
            logger.error(f'cognito user params {params}')
            logger.error(f'cognito user {cognito_user}')
            logger.error(f'user_params {user_params}')
            return cognito_user.get('User')

        except ParamValidationError as ex:
            logger.error(f'BOTOCORE_EXCEPTIONS {ex}')
            raise CognitoException.create_from_boto_exception(ex)

        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def set_user_mfa_preference(self, enable, access_token):

        params = {
            'SMSMfaSettings': {'Enabled': enable},
            'AccessToken': access_token,
        }

        try:
            data = self.client.set_user_mfa_preference(**params)
            return data
        except constants.AWS_EXCEPTIONS as ex:
            raise CognitoException.create_from_exception(ex)

    def admin_disable_user(self):
        pass

    def admin_delete_user(self):
        pass

    def admin_confirm_sign_up(self):
        pass

    def admin_update_user_attributes(self):
        pass

    def resend_confirmation_code(self):
        pass

    def admin_list_users(self):
        pass






