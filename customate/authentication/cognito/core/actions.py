from authentication.cognito import utils
from authentication.cognito.core import constants
from authentication.cognito.core.base import CognitoClient, CognitoException, CognitoUser
# DON'T remove this import
from authentication.cognito.middleware import helpers as mid_helpers

import logging

logger = logging.getLogger(__name__)


def respond_to_auth_challenge(username, challenge_name, responses, session=None):
    responses['USERNAME'] = username
    responses['SECRET_HASH'] = utils.get_cognito_secret_hash(username)

    try:
        return CognitoClient().client.respond_to_auth_challenge(ClientId=constants.CLIENT_ID,
                                                              ChallengeName=challenge_name,
                                                              ChallengeResponses=responses,
                                                              Session=session)

    except constants.AWS_EXCEPTIONS as ex:
        raise CognitoException.create_from_exception(ex)


def confirm_forgot_password(username, code, new_password):
    secret_hash = utils.get_cognito_secret_hash(username)

    try:
        return CognitoClient.client.confirm_forgot_password(ClientId=constants.CLIENT_ID, SecretHash=secret_hash,
                                                            Username=username,
                                                            Password=new_password,
                                                            ConfirmationCode=code)
    except constants.AWS_EXCEPTIONS as ex:
        raise CognitoException.create_from_exception(ex)


def admin_get_user(username):
    try:
        return CognitoClient.client.admin_get_user(UserPoolId=constants.POOL_ID, Username=username)
    except constants.AWS_EXCEPTIONS as ex:
        raise CognitoException.create_from_exception(ex)


def admin_disable_user(username):
    result = CognitoClient.client.admin_disable_user(UserPoolId=constants.POOL_ID, Username=username)

    return result


def admin_delete_user(username):
    result = CognitoClient.client.admin_delete_user(UserPoolId=constants.POOL_ID, Username=username)

    return result


def admin_create_user(username, user_attributes, temporary_password, suppress=False):
    message_action = 'SUPPRESS' if suppress else 'RESEND'

    result = CognitoClient.client.admin_create_user(UserPoolId=constants.POOL_ID, Username=username,
                                                    TemporaryPassword=temporary_password, MessageAction=message_action,
                                                    UserAttributes=user_attributes)

    return result


def admin_update_user_attributes(username, user_attributes):
    try:
        return CognitoClient.client.admin_update_user_attributes(UserPoolId=constants.POOL_ID, Username=username,
                                                                 UserAttributes=user_attributes)
    except constants.AWS_EXCEPTIONS as ex:
        raise CognitoException.create_from_exception(ex)


def resend_confirmation_code(username):
    result = CognitoClient.client.resend_confirmation_code(ClientId=constants.CLIENT_ID, Username=username,
                                                           SecretHash=utils.get_cognito_secret_hash(username))

    return result


def admin_list_users(attributes_to_get=None, pagination_token=None):
    args = {'UserPoolId': constants.POOL_ID}

    if attributes_to_get:
        args['AttributesToGet'] = attributes_to_get
    if pagination_token:
        args['PaginationToken'] = pagination_token

    result = CognitoClient.client.list_users(**args)

    return result