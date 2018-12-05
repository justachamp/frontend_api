# This will validate an incoming token and ensure that it is valid, and refresh it if required
#
# It will either return a new access token if it needed to refresh the existing one, None if the token
# was validated and didn't need to be refreshed, or raise an Exception if it can't validate the token
import base64
import datetime
import json
import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from authentication import settings
from authentication.cognito import utils
from authentication.cognito.core import constants, actions
from authentication.cognito.utils import PublicKey

# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


def validate_token(access_token, id_token, refresh_token=None):

    try:
        header, payload = decode_token(access_token)
        id_header, id_payload = decode_token(id_token)
        logger.error(f'id_payload {id_payload}')
    except Exception as ex:
        # Invalid token or token we can't decode for whatever reason
        raise Exception("Invalid token")

    public_keys = utils.get_public_keys()

    [matching_key] = [key for key in public_keys['keys'] if key['kid'] == header['kid']]
    [id_matching_key] = [key for key in public_keys['keys'] if key['kid'] == id_header['kid']]
    if matching_key is None or id_matching_key is None:
        raise Exception("Invalid token public key")
    else:
        # Verify signature using the public key for this pool, as defined the the AWS documentation
        decode = jwt.decode(access_token, PublicKey(matching_key).pem, algorithms=[header['alg']],
                            options={'verify_exp': False})
        pass

    # TODO: Documentation says aud should be the key, but this doesn't exist and client_id has the data aud
    # should have
    #
    # Verify that the audience matches the Cognito app ID, as defined by the AWS documentation
    if payload['client_id'] != constants.CLIENT_ID:
        raise Exception("Invalid token audience")

    # Verify that the issuer matches the URL for the Cognito user pool, as defined by the AWS documentation
    if payload['iss'] != id_payload['iss'] or id_payload['iss'] != "https://cognito-idp." + constants.POOL_ID.split("_", 1)[0] + ".amazonaws.com/" \
            + constants.POOL_ID:
        raise Exception("Invalid token issuer")

    # Verify that the token is either not expired, or if expired, that we have a refresh token to refresh it
    if payload['exp'] <= datetime.datetime.timestamp(datetime.datetime.utcnow()) or \
            id_payload['exp'] <= datetime.datetime.timestamp(datetime.datetime.utcnow()):

        if not refresh_token:
            # The current access token is expired and no refresh token was provided, authentication fails
            raise Exception("The access token provided has expired. Please login again.")
        else:
            # This token is expired, potentially check for a refresh token? Return this token in the auth return
            # variable?

            result = actions.initiate_auth(payload['username'], constants.REFRESH_TOKEN_FLOW,
                                           refresh_token=refresh_token)

            if result['AuthenticationResult']:
                # Return the freshly generated access token as an indication auth succeeded but a new token was
                # required
                #
                # TODO: DON'T return refresh token here, for methods that require a refresh token we should implement
                # them somewhere else, or differently
                data = result['AuthenticationResult']
                logger.error(f"tokens {data['AccessToken']}, {data['IdToken']}, {refresh_token}")
                return data['AccessToken'], data['IdToken'], refresh_token
            else:
                # Something went wrong with the authentication
                raise Exception("An error occurred while attempting to refresh the access token")
    else:
        # The token validated successfully, we don't need to do anything else here
        logger.error(f"tokens None, None, None")
        return None, None, None


def decode_token(access_token):
    token_parts = access_token.split(".")

    header = json.loads(
        base64.b64decode(token_parts[0] + "=" * ((4 - len(token_parts[0]) % 4) % 4)).decode('utf-8'))
    payload = json.loads(
        base64.b64decode(token_parts[1] + "=" * ((4 - len(token_parts[1]) % 4) % 4)).decode('utf-8'))

    return header, payload


def process_request(request, propogate_error=False):
    try:
        # logger.error('process_request helpels')
        # logger.error(f'meta {request.META}')
        access_token = request.META.get('HTTP_ACCESSTOKEN')
        refresh_token = request.META.get('HTTP_REFRESHTOKEN')
        id_token = request.META.get('HTTP_IDTOKEN')
        logger.error(f'access_token: {access_token} refresh_token: {refresh_token}  id_token: {id_token}')
        if not access_token or not refresh_token or not id_token:
            # Need to have this to authenticate, error out
            raise Exception("No valid tokens were found in the request")
        else:
            # logger.error('start validation')
            new_access_token, new_id_token, new_refresh_token = validate_token(access_token, id_token, refresh_token)

            # logger.error(f'new_access_token: {new_access_token} new_refresh_token: {new_refresh_token}')
            header, payload = decode_token(access_token)
            logger.error(f'header: {header} payload: {payload}')
            id_header, id_payload = decode_token(id_token)
            logger.error(f'header: {id_header} payload: {id_payload}')
            try:
                user = get_user_model().objects.get(username=id_payload['email'])
            except Exception as ex:
                logger.error(f'process_request {ex} {payload["username"]}')
                if propogate_error:
                    raise ex

                if settings.AUTO_CREATE_USER:
                    aws_user = actions.admin_get_user(payload['username'])

                    user_attributes = {k: v for dict in [{d['Name']: d['Value']} for d in aws_user['UserAttributes']]
                                       for k, v in dict.items()}
                    logger.error(f'process_request user_attributes: {user_attributes}')
                    user = get_user_model().objects.create(username=payload['email'], email=user_attributes['email'],
                                                           first_name=user_attributes['given_name'],
                                                           last_name=user_attributes['family_name'])

                    user.save()
                else:
                    return AnonymousUser, None, None, None

        return user, new_access_token, new_id_token, new_refresh_token

    except Exception as ex:
        logger.error(f'process_request Exception: {ex}')
        if propogate_error:
            raise ex
        return AnonymousUser(), None, None, None
