from django.conf import settings
from django.contrib.auth import get_user_model
from authentication.cognito.core import constants
from authentication.cognito import utils
from external_apis.aws.service import get_aws_client

import logging

logger = logging.getLogger(__name__)
User = get_user_model()


def generate_password():
    part1 = User.objects.make_random_password(3, 'abcdefghjkmnpqrstuvwxyz')
    part2 = User.objects.make_random_password(3, 'ABCDEFGHJKLMNPQRSTUVWXYZ')
    part3 = User.objects.make_random_password(3, '123456789')
    return f'{part1}-{part2}-{part3}'


class CognitoClient:
    client = get_aws_client('cognito-idp')


class CognitoException(Exception):
    def __init__(self, message, status):
        super(CognitoException, self).__init__(message)

        self.status = status

    @staticmethod
    def create_from_exception(ex):
        return CognitoException(ex.response['Error']['Message'], ex.response['ResponseMetadata']['HTTPStatusCode'])


class CognitoUser(CognitoClient):
    user_class = User

    def _prepare_kwargs(self, kwargs):
        try:
            if not kwargs.get('SecretHash'):
                del kwargs['SecretHash']
        finally:
            return kwargs

    def sign_up(self, username, password, user_attributes, validation_data=None):
        logger.info("Sign up with CognitoUser class (username=%s, user_attributes=%s)" % (username, user_attributes))

        secret_hash = utils.get_cognito_secret_hash(username)
        params = {"ClientId": constants.CLIENT_ID,
                  "Username": username, "Password": password,
                  "UserAttributes": user_attributes}

        if validation_data:
            params['ValidationData'] = validation_data

        if secret_hash:
            params['SecretHash'] = secret_hash

        user_params = utils.cognito_to_dict(user_attributes, settings.COGNITO_ATTR_MAPPING)
        logger.debug(f'User params: {user_params}')
        cognito_user = CognitoClient.client.sign_up(**params)
        logger.debug(f'Cognito user: {cognito_user}')
        user = self.user_class.objects.create(
            username=username, email=username, cognito_id=cognito_user['UserSub']
        )

        user.save()
        return cognito_user

    def initiate_auth(self, auth_flow, auth_parameters):
        logger.info("Initiating auth with CognitoUser class (auth_flow=%s)" % auth_flow)

        secret_hash = utils.get_cognito_secret_hash(auth_parameters.get('USERNAME'))
        if secret_hash:
            auth_parameters['SECRET_HASH'] = secret_hash
        res = self.client.initiate_auth(AuthFlow=auth_flow, ClientId=constants.CLIENT_ID,
                                        AuthParameters=auth_parameters)

        return res
