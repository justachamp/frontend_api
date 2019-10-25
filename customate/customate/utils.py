import inspect
import logging
from rest_framework_json_api.utils import format_value
from django.utils import encoding, six
from rest_framework import exceptions
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


"""
Improved version of rest_framework_json_api.utils.format_drf_errors:
1) Prevent sending object in "detail" field like here:
{
  "errors": [
    {
      "detail": {
        "email": "Someone's already using that e-mail"
      },
      "source": {
        "pointer": "/data/attributes/user"
      },
      "status": "400"
    }
  ]
}

2) Set correct "source.pointer" field for nested fields (compare with example above):
{
  "errors": [
    {
      "detail": "Someone's already using that e-mail",
      "source": {
        "pointer": "/data/attributes/user/email"
      },
      "status": "400"
    }
  ]
}
"""
def format_drf_errors(response, context, exc):
    errors = []
    # handle generic errors. ValidationError('test') in a view for example
    if isinstance(response.data, list):
        for message in response.data:
            errors.append(format_error_item(message, '/data', response.status_code))
    # handle all errors thrown from serializers
    else:
        for field, error in response.data.items():
            field = format_value(field)
            pointer = '/data/attributes/{}'.format(field)
            # see if they passed a dictionary to ValidationError manually
            if isinstance(error, dict):
                errors.append(error)
            elif isinstance(error, six.string_types):
                classes = inspect.getmembers(exceptions, inspect.isclass)
                # DRF sets the `field` to 'detail' for its own exceptions
                if isinstance(exc, tuple(x[1] for x in classes)):
                    pointer = '/data'

                errors.append(format_error_item(error, pointer, response.status_code))
            elif isinstance(error, list):
                for message in error:
                    # Sending separate errors with updated "source.pointer" field requires a lot of changes on frontend
                    # so we keep the old format for now
                    # if isinstance(message, dict):
                    #     for subfield, detail in message.items():
                    #         subfield_pointer = "{}/{}".format(pointer, subfield)
                    #         errors.append(format_error_item(detail, subfield_pointer, response.status_code))
                    # else:
                    errors.append(format_error_item(message, pointer, response.status_code))
            else:
                errors.append(format_error_item(error, pointer, response.status_code))

    context['view'].resource_name = 'errors'
    response.data = errors

    return response


def format_error_item(detail, pointer, status):
    return {
        'detail': detail,
        'source': {
            'pointer': pointer,
        },
        'status': encoding.force_text(status),
    }
