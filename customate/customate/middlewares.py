import logging
from traceback import format_exc
from customate.settings import DEBUG
from rest_framework import status as status_codes

logger = logging.getLogger(__name__)


def grepify_exception(exc, delimiter=" | "):
    """
    Turns exception into one line string convenient for log grepping
    :param exc: Python's exception
    :type exc: Exception
    :param delimiter: Separator between newlines
    :type delimiter: str
    :rtype: unicode
    """

    fe = format_exc()
    fe = fe.replace("\n", delimiter)
    return fe


class RequestDetailsLoggingMiddleware:
    def __init__(self, get_response=None):
        # One-time configuration and initialization.
        self.get_response = get_response
        super().__init__()

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.
        logging.init_shared_extra()

        logger.info("Request details: url=%s, method=%s", request.get_full_path(), request.method,
                    extra={'body': request.body.decode("utf-8"),
                           'query_params': request.GET.copy(),
                           'url': request.get_full_path(),
                           'method': request.method})

        response = self.get_response(request)

        response_body = None
        if self._should_log_response_body(request, response):
            response_body = response.content.decode('utf-8') \
                if response.content and hasattr(response.content, 'decode') and callable(response.content.decode) \
                else None

        logger.info("Response details: status_code=%s", response.status_code,
                    extra={'status_code': response.status_code,
                           'body': response_body,
                           'logGlobalDuration': True
                           })

        # Code to be executed for each request/response after
        # the view is called.
        return response

    def _should_log_response_body(self, request, response):
        """
        Don't want to log massive, not really interesting response related information
        """
        return response.status_code >= status_codes.HTTP_204_NO_CONTENT

    def process_exception(self, request, exception):
        """

        :param exception:
        :return:
        """
        if not DEBUG:
            logger.error(grepify_exception(exception))
        return None
