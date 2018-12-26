from django.contrib.auth.models import User, AnonymousUser
from authentication.cognito.core.helpers import initiate_auth
from authentication.cognito.middleware import helpers as m_helpers
# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)

# This is utilised when doing username and password validation and calling the authenticate method from
# django.contrib.auth (currently not actually used?)
class AwsDjangoAuthentication:

    def authenticate(self, request, username=None, password=None):
        # This is where we will extract information about the incoming access token from the user,
        # and decide whether or not they are authenticated
        logger.error('authenticate AwsDjangoAuthentication')
        logger.error(f'request {request}')
        logger.error(f'user {user}')
        # TODO: Remove this hackiness. Should only return a user from this method as Django seems to only expect a user
        # and not a tuple with a token
        if username is None:
            user, _, _, _ = m_helpers.process_request(request)

            return user
        else:
            try:
                # We've received a username and password, do that authentication flow instead
                result = initiate_auth({"username":username, "password": password, "auth_flow": "USER_PASSWORD_AUTH"})

                return User.objects.get(email=username)
            except Exception as ex:
                # Either couldn't authenticate or user didn't exist, throw an error
                return AnonymousUser()

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None