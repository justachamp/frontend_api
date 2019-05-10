from django.conf import settings
from authentication.cognito.middleware import helpers
# import the logging library
import logging

# Get an instance of a logger
logger = logging.getLogger(__name__)


# This is utilised from normal Django views. Currently used for anything that requires authentication but isn't
# already utilising rest framework
class AwsDjangoMiddleware:

    def __call__(self, request):
        logger.info('call AwsDjangoMiddleware')

        # Get the user and a new token if required
        user, token, id_token, refresh_token = helpers.process_request(request)

        request.user = user
        logger.info(f'AwsDjangoMiddleware {user}')
        response = self.get_response(request)

        if token:
            # TODO: Set the token in the response here as well? If the user hits here, they're still active
            http_only = settings.HTTP_ONLY_COOKIE
            secure = settings.SECURE_COOKIE

            response.set_cookie(key='AccessToken', value=token, secure=secure, httponly=http_only)
            response.set_cookie(key="IdToken", value=id_token, secure=secure, httponly=http_only)
            response.set_cookie(key="RefreshToken", value=refresh_token, secure=secure, httponly=http_only)
            pass

        return response

    def process_request(self, request):
        pass
