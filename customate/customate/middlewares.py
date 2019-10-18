import logging

from rest_framework import status as status_codes

logger = logging.getLogger(__name__)


class RequestDetailsLoggingMiddleware:
    def __init__(self, get_response=None):
        # One-time configuration and initialization.
        self.get_response = get_response
        super().__init__()

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        logging.init_shared_extra()

        logger.info("Request details: url=%s, method=%s", request.path, request.method,
                    extra={'body': request.body.decode("utf-8")})

        response = self.get_response(request)

        if self._should_log_response(request, response):
            logger.info("Response details: status=%s", response.status_code,
                        extra={'body': response.content.decode('utf-8') if response.content else None})

        # Code to be executed for each request/response after
        # the view is called.
        return response

    def _should_log_response(self, request, response):
        """
        Don't want to log massive, not really interesting response related information
        """
        return response.status_code >= status_codes.HTTP_204_NO_CONTENT
