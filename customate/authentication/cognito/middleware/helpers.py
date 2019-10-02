# This will validate an incoming token and ensure that it is valid, and refresh it if required
#
# It will either return a new access token if it needed to refresh the existing one, None if the token
# was validated and didn't need to be refreshed, or raise an Exception if it can't validate the token
import logging
import base64
import datetime
import json
import jwt
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from authentication.cognito import utils
from authentication.cognito.core import constants, service, helpers
from authentication.cognito.exceptions import TokenIssue
from authentication.cognito.utils import PublicKey
from rest_framework.exceptions import AuthenticationFailed

# Get an instance of a logger
logger = logging.getLogger(__name__)
identity = service.Identity()


def validate_token(access_token, id_token, refresh_token=None):
    try:
        header, payload = decode_token(access_token)
        if id_token:
            id_header, id_payload = decode_token(id_token)
            logger.debug(f'id_payload {id_payload}')
    except Exception as ex:
        # Invalid token or token we can't decode for whatever reason
        logger.error(f"Validating token process caught an exception: {ex!r}")
        raise AuthenticationFailed("Unable to decode token")

    public_keys = utils.get_public_keys()
    [matching_key] = [key for key in public_keys['keys'] if key['kid'] == header['kid']]

    try:
        if matching_key is None:
            raise Exception("Invalid token public key")
        else:
            # Verify signature using the public key for this pool, as defined the the AWS documentation
            pem = PublicKey(matching_key).pem
            jwt.decode(access_token, pem, algorithms=[header['alg']], options={'verify_exp': False})
    except Exception as ex:
        logger.error(f'Token signature verification failed: {ex!r}')
        raise AuthenticationFailed("Token signature verification failed")

    # Verify that the audience matches the Cognito app ID, as defined by the AWS documentation
    if payload['client_id'] != constants.CLIENT_ID:
        raise AuthenticationFailed("Invalid token audience")

    # Verify that the issuer matches the URL for the Cognito user pool, as defined by the AWS documentation
    aws_region, _ = constants.POOL_ID.split("_", 1)
    if payload['iss'] != "https://cognito-idp.%s.amazonaws.com/%s" % (aws_region, constants.POOL_ID):
        raise AuthenticationFailed("Invalid token issuer")

    # Verify that the token is either not expired, or if expired, that we have a refresh token to refresh it
    if payload['exp'] <= datetime.datetime.timestamp(datetime.datetime.utcnow()):
        if not refresh_token:
            # The current access token is expired and no refresh token was provided, authentication fails
            raise AuthenticationFailed("The access token provided has expired. Please login again.")

        # This token is expired, potentially check for a refresh token?
        # Return this token in the auth return variable?
        result = identity.initiate_auth(payload['username'], constants.REFRESH_TOKEN_FLOW,
                                        refresh_token=refresh_token)

        if result['AuthenticationResult']:
            # Return the freshly generated access token as an indication auth succeeded but a new token was
            # required
            # TODO: DON'T return refresh token here, for methods that require a refresh token we should implement
            # them somewhere else, or differently
            data = result['AuthenticationResult']
            logger.debug(f"Got fresh tokens: {data['AccessToken']}, {data['IdToken']}, {refresh_token}")
            return data['AccessToken'], data['IdToken'], refresh_token
        else:
            # Something went wrong with the authentication
            raise AuthenticationFailed("Empty AuthenticationResult. Please login again")

    # The token validated successfully, we don't need to do anything else here
    logger.debug(f"tokens None, None, None")
    return None, None, None


def decode_token(access_token):
    token_parts = access_token.split(".")
    header = json.loads(base64.b64decode(token_parts[0] + "=" * ((4 - len(token_parts[0]) % 4) % 4)).decode('utf-8'))
    payload = json.loads(base64.b64decode(token_parts[1] + "=" * ((4 - len(token_parts[1]) % 4) % 4)).decode('utf-8'))
    return header, payload


def process_request(request, propagate_error=False):
    access_token = request.META.get('HTTP_ACCESSTOKEN')
    refresh_token = request.META.get('HTTP_REFRESHTOKEN')
    id_token = request.META.get('HTTP_IDTOKEN')

    return get_tokens(access_token=access_token, id_token=id_token, refresh_token=refresh_token,
                      propagate_error=propagate_error)


def get_tokens(access_token, id_token=None, refresh_token=None, propagate_error=False):
    logger.debug(f'access_token: {access_token}')
    logger.debug(f'refresh_token: {refresh_token}')
    logger.debug(f'id_token: {id_token}')

    try:
        if not access_token:
            # Need to have this to authenticate, error out
            raise TokenIssue("No valid Access token were found in the request")

        new_access_token, new_id_token, new_refresh_token = validate_token(access_token, id_token, refresh_token)
        logger.debug(f'new_access_token: {new_access_token} new_refresh_token: {new_refresh_token}')

        header, payload = decode_token(access_token)
        logger.debug(f'header: {header} payload: {payload}')
        if id_token:
            id_header, id_payload = decode_token(id_token)
            logger.debug(f'header: {id_header} payload: {id_payload}')
        else:
            id_payload = None

        try:
            if id_payload:
                user = get_user_model().objects.get(cognito_id=id_payload.get('cognito:username'))
            else:
                user = get_user_model().objects.get(cognito_id=payload.get('username'))
        except Exception as ex:
            logger.error(f'process_request {ex!r} {payload["cognito:username"]}')
            if propagate_error:
                raise ex
            return AnonymousUser, None, None, None

        cognito_user = None
        try:
            cognito_user = helpers.get_user({'access_token': access_token})
        except Exception as ex:
            if not cognito_user or not ('Username' in cognito_user):
                raise AuthenticationFailed("No valid Access token were found in the request")
            logger.error(f'{ex!r}')

        return user, new_access_token, new_id_token, new_refresh_token

    except AuthenticationFailed as ex:
        logger.debug(f'{ex!r}')
        raise ex

    except TokenIssue as ex:
        logger.debug(f'{ex!r}')
        if propagate_error:
            raise ex
        return AnonymousUser(), None, None, None

    except Exception as ex:
        logger.error(f'Receiving tokens process caught an exception: {ex!r}')
        if propagate_error:
            raise ex
        return AnonymousUser(), None, None, None
