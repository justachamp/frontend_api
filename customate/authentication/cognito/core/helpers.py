from authentication.cognito.core import constants
from authentication.cognito.core.service import Identity

# Collection of methods intended to make the calling of AWS Cognito methods a bit easier. Each method expects both a
# data parameter (which will be a dictionary of values) and an optional param_mapping parameter - another dictionary
# which can be used to override the name of expected values in the data dictionary.
#
# Main use case is when receiving data from a HTTP request - rather than parse it all out individually, just give
# the data to this method with the right naming/mapping, and it'll handle it for you

BAD_DATA_EXCEPTION = "The required parameters were not passed through in the data dictionary"

import logging
logger = logging.getLogger(__name__)

# TODO: Possibly change some of these methods to just accept one parameter where appropriate (i.e. just a username)

identity = Identity()


def initiate_auth(data, param_mapping=None):
    if ("username" in data and "password" in data) or ("username" in param_mapping and "password" in param_mapping):
        auth_flow = constants.CUSTOM_FLOW if data.get('custom_flow') else constants.USER_PASSWORD_FLOW
        username = parse_parameter(data, param_mapping, "username")
        password = parse_parameter(data, param_mapping, "password")

        return identity.initiate_auth(username, auth_flow, password)

    else:
        raise ValueError("Unsupported auth flow")


def sign_out(data, param_mapping=None):
    if ("access_token" in data) or ("access_token" in param_mapping):
        access_token = parse_parameter(data, param_mapping, "access_token")
        return identity.sign_out(access_token=access_token)

    else:
        raise ValueError("Unsupported auth flow")


def admin_sign_out(data, param_mapping=None):
    if ("username" in data) or ("username" in param_mapping):
        username = parse_parameter(data, param_mapping, "username")

        return identity.admin_sign_out(username=username)

    else:
        raise ValueError("Unsupported auth flow")


def refresh_session(data, param_mapping=None):
    if ("username" in data and "refresh_token" in data) or ("username" in param_mapping and "refresh_token" in param_mapping):
        auth_flow = constants.REFRESH_TOKEN_FLOW
        username = parse_parameter(data, param_mapping, "username")
        refresh_token = parse_parameter(data, param_mapping, "refresh_token")

        return identity.refresh_session(username, auth_flow, refresh_token=refresh_token)

    else:
        raise ValueError("Unsupported auth flow")


def verification_code(data, param_mapping=None):
    if ("attribute_name" in data and "access_token" in data) \
            or ("attribute_name" in param_mapping and "access_token" in param_mapping):

        attribute_name = parse_parameter(data, param_mapping, "attribute_name")
        access_token = parse_parameter(data, param_mapping, "access_token")

        return identity.verification_code(attribute_name=attribute_name, access_token=access_token)

    else:
        raise ValueError("Unsupported auth flow")


def verify_attribute(data, param_mapping=None):
    if ("attribute_name" in data and "access_token" in data and "code" in data) \
            or ("attribute_name" in param_mapping and "access_token" in param_mapping and "code" in param_mapping):

        attribute_name = parse_parameter(data, param_mapping, "attribute_name")
        access_token = parse_parameter(data, param_mapping, "access_token")
        code = parse_parameter(data, param_mapping, "code")

        return identity.verify_attribute(attribute_name=attribute_name, access_token=access_token, code=code)

    else:
        raise ValueError("Unsupported auth flow")


def respond_to_auth_challenge(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
        challenge_name = parse_parameter(data, param_mapping, 'challenge_name')
        responses = parse_parameter(data, param_mapping, 'challenge_response')
        session = parse_parameter(data, param_mapping, 'session')
    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.respond_to_auth_challenge(username=username, challenge_name=challenge_name,
                                              responses=responses, session=session)


def sign_up(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
        password = parse_parameter(data, param_mapping, 'password')
        account_type = parse_parameter(data, param_mapping, 'account_type')
        user_attributes = parse_parameter(data, param_mapping, 'user_attributes')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.sign_up(username, password, account_type, user_attributes)


def confirm_sign_up(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
        confirmation_code = parse_parameter(data, param_mapping, 'code')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.confirm_sign_up(username, confirmation_code)


def forgot_password(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.forgot_password(username)


def change_password(data, param_mapping=None):
    try:
        previous = parse_parameter(data, param_mapping, 'previous')
        proposed = parse_parameter(data, param_mapping, 'proposed')
        access_token = parse_parameter(data, param_mapping, 'access_token')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.change_password(previous, proposed, access_token)


def restore_password(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
        password = parse_parameter(data, param_mapping, 'password')
        code = parse_parameter(data, param_mapping, 'code')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.restore_password(username, code, password)


def get_user(data, param_mapping=None):
    try:
        access_token = parse_parameter(data, param_mapping, 'access_token')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.get_user(access_token)


def admin_get_user(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.admin_get_user(username)


def admin_update_user_attributes(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
        user_attributes = parse_parameter(data, param_mapping, 'user_attributes')
    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.admin_update_user_attributes(username, user_attributes)


def admin_disable_user(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.admin_disable_user(username)


def admin_delete_user(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.admin_delete_user(username)


def admin_create_user(data, param_mapping=None):
    try:
        username = parse_parameter(data, param_mapping, 'username')
        user_attributes = parse_parameter(data, param_mapping, 'user_attributes')
        temporary_password = parse_parameter(data, param_mapping, 'temporary_password')
        action = parse_parameter(data, param_mapping, 'action')
        delivery = parse_parameter(data, param_mapping, 'delivery')
        # if "suppress" in data or "suppress" in param_mapping:
        #     supress = parse_parameter(data, param_mapping, 'suppress')

    except Exception as ex:
        raise ValueError(BAD_DATA_EXCEPTION)

    return identity.admin_create_user(username, user_attributes, temporary_password, action, delivery)


def parse_parameter(data, param_mapping, param=None):
    if param_mapping is not None:
        if param in param_mapping:
            return data[param_mapping[param]]
    else:
        return data[param]
