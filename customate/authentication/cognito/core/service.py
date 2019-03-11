from django.conf import settings
import boto3
from botocore.exceptions import ParamValidationError
from authentication.cognito.core import constants
from authentication.cognito import utils
from core.services.user import UserService

# import the logging library
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)

BUSINESS_ACCOUNT = 'business'
BAD_DATA_EXCEPTION = "The required parameters were not passed through in the data dictionary"
COGNITO_CONFIRMED_STATUS ='CONFIRMED'
COGNITO_ENABLED_USER_STATUS ='CONFIRMED'
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

    _user_service = None

    @property
    def user_service(self):
        if not self._user_service:
            self._user_service = UserService()

        return self._user_service

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
            self.user_service.create_user(username, account_type, cognito_user['UserSub'])
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

    def confirm_sign_up(self, username, confirmation_code):
        try:
            secret_hash = utils.get_cognito_secret_hash(username)

            params = {
                'ClientId': constants.CLIENT_ID,
                'Username': username,
                'ForceAliasCreation': False,
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

    @staticmethod
    def is_confirmed(user):
        return user and user.get("UserStatus") == COGNITO_CONFIRMED_STATUS

    @staticmethod
    def is_enabled(user):
        return user and user.get('Enabled')

    def _can_pass_mfa(self, username):
        cognito_user = self.admin_get_user(username)
        if not self.is_enabled(cognito_user) or not self.is_confirmed(cognito_user):
            return True

        for attr in cognito_user.get('UserAttributes', {}):
            if attr.get('Name') == 'phone_number_verified':
                return attr.get('Value') == 'true'
        return False

    def initiate_auth(self, username, auth_flow, password=None, refresh_token=None):
        auth_parameters = {}
        secret_hash = utils.get_cognito_secret_hash(auth_parameters.get('USERNAME'))
        if secret_hash:
            auth_parameters['SECRET_HASH'] = secret_hash

        if auth_flow in (constants.USER_PASSWORD_FLOW, constants.CUSTOM_FLOW):
            if auth_flow == constants.USER_PASSWORD_FLOW and not self._can_pass_mfa(username):
                auth_flow = constants.CUSTOM_FLOW

            auth_parameters['USERNAME'] = username
            auth_parameters['PASSWORD'] = password
        elif auth_flow in (constants.REFRESH_TOKEN_AUTH_FLOW, constants.REFRESH_TOKEN_FLOW):
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

    def admin_sign_out(self, username):
        try:
            return self.client.admin_user_global_sign_out(
                UserPoolId=constants.POOL_ID,
                Username=username
            )
        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def verification_code(self, attribute_name, access_token):
        try:
            result = self.client.get_user_attribute_verification_code(
                AttributeName=attribute_name,
                AccessToken=access_token
            )

            if attribute_name == 'phone_number':
                self.set_user_mfa_preference(enable=False, access_token=access_token)

            return result
        except constants.AWS_EXCEPTIONS as ex:
            logger.error(f'AWS_EXCEPTIONS {ex}')
            raise CognitoException.create_from_exception(ex)

        except Exception as ex:
            logger.error(f'general {ex}')
            raise Exception(ex)

    def verify_attribute(self, attribute_name, access_token, code):
        try:
            result = self.client.verify_user_attribute(
                AttributeName=attribute_name,
                AccessToken=access_token,
                Code=code
            )

            if attribute_name == 'phone_number':
                self.set_user_mfa_preference(enable=True, access_token=access_token)

            return result
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

    def change_password(self, previous, proposed, access_token):
        params = {
            'PreviousPassword': previous,
            'ProposedPassword': proposed,
            'AccessToken': access_token
        }

        try:
            data = self.client.change_password(**params)
            return data
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

    def get_user(self, access_token):
        params = {
            'AccessToken': access_token,
        }

        try:
            data = self.client.get_user(**params)
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

    def admin_update_user_attributes(self, username, user_attributes):
        params = {
            'UserPoolId': constants.POOL_ID,
            'Username': username,
            'UserAttributes': user_attributes
        }

        try:
            data = self.client.admin_update_user_attributes(**params)
            return data
        except constants.AWS_EXCEPTIONS as ex:
            raise CognitoException.create_from_exception(ex)

    def resend_confirmation_code(self):
        pass

    def admin_list_users(self):
        pass






