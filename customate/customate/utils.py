import logging
from rest_framework_json_api.utils import format_drf_errors
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


def exception_handler(exc, context):
    """
    Custom error handler to comply with JSON API error format.
    Example response.data:

    {
        "errors": [
            {
                "detail": "Schedule with such name already exists",
                "source": {
                    "pointer": "/data/attributes/name"
                },
                "status": "400"
            },
            {
                "detail": "This field is required.",
                "source": {
                    "pointer": "/data/attributes/payment_amount"
                },
                "status": "400"
            }
        ]
    }

    :param exc:
    :param context:
    :return:
    """
    # Render exception with DRF
    response = drf_exception_handler(exc, context)
    if not response:
        return response

    # format errors according to JSON API
    response = format_drf_errors(response, context, exc)
    logger.debug("DRF JSON error reply: %r " % response.data)
    return response
