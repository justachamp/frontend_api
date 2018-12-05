from django.conf import settings
import boto3
from django.contrib.auth import get_user_model
from authentication.cognito.core import constants
from authentication.cognito import utils
# import the logging library
import logging
# Get an instance of a logger
logger = logging.getLogger(__name__)


class CognitoClient:
    client = boto3.client('cognito-idp', aws_access_key_id=settings.AWS_ACCESS_KEY,
                          aws_secret_access_key=settings.AWS_SECRET_KEY, region_name=settings.AWS_REGION)


class CognitoException(Exception):
    def __init__(self, message, status):
        super(CognitoException, self).__init__(message)

        self.status = status

    @staticmethod
    def create_from_exception(ex):
        return CognitoException(ex.response['Error']['Message'], ex.response['ResponseMetadata']['HTTPStatusCode'])


class CognitoUser(CognitoClient):
    user_class = get_user_model()

    def _prepare_kwargs(self, kwargs):
        try:
            if not kwargs.get('SecretHash'):
                del kwargs['SecretHash']
        finally:
            return kwargs

    def sign_up(self, username, password, user_attributes, validation_data=None):
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
        cognito_user = CognitoClient.client.sign_up(**params)
        logger.error(f'cognito user {cognito_user}')
        logger.error(f'user_params {user_params}')
        user = self.user_class.objects.create(
            username=username, email=username, cognito_id=cognito_user['UserSub']
            # first_name=user_params.get('given_name'), last_name=user_params.get('family_name')
        )

        user.save()
        return cognito_user




    def confirm_sign_up(self, username, confirmation_code, force_alias_creation):

        secret_hash = utils.get_cognito_secret_hash(username)

        params = {
            'ClientId': constants.CLIENT_ID,
            'Username': username,
            'ForceAliasCreation': force_alias_creation,
            'ConfirmationCode': confirmation_code
        }

        if secret_hash:
            params['SecretHash'] = secret_hash

        return CognitoClient.client.confirm_sign_up(**params)

    def initiate_auth(self, auth_flow, auth_parameters):
        # logger.error(f'auth_parameters: {auth_parameters} {auth_flow}')
        secret_hash = utils.get_cognito_secret_hash(auth_parameters.get('USERNAME'))
        if secret_hash:
            auth_parameters['SECRET_HASH'] = secret_hash
        res = self.client.initiate_auth(AuthFlow=auth_flow, ClientId=constants.CLIENT_ID,
                                         AuthParameters=auth_parameters)

        # logger.error(f'init auth: {res}')

        return res
