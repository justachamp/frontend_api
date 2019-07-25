import logging
from traceback import format_exc

from rest_framework_json_api.serializers import Serializer as JSONAPISerializer
from rest_framework_json_api.serializers import (
    SkipField,
    Mapping,
    OrderedDict,
    api_settings,
    set_value,
    get_error_detail,
    ValidationError,
    DjangoValidationError,
)

logger = logging.getLogger(__name__)


class BulkExtensionMixin(object):
    def get_serializer(self, *args, **kwargs):
        is_bulk = isinstance(getattr(self.request, 'data', None), list)
        kwargs['many'] = kwargs.pop('many', is_bulk)
        return super().get_serializer(*args, **kwargs)


class Serializer(JSONAPISerializer):

    def to_internal_value(self, data):
        """
        Dict of native values <- Dict of primitive datatypes.
        """
        logger.info("Serializer: to_internal_value! %r " % data)

        if not isinstance(data, Mapping):
            message = self.error_messages['invalid'].format(
                datatype=type(data).__name__
            )
            raise ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: [message]
            }, code='invalid')

        ret = OrderedDict()
        errors = OrderedDict()
        fields = self._writable_fields

        for field in fields:
            validate_method = getattr(self, 'validate_' + field.field_name, None)
            primitive_value = field.get_value(data)
            try:
                validated_value = field.run_validation(primitive_value)
                if validate_method is not None:
                    validated_value = validate_method(validated_value)
            except ValidationError as exc:
                logger.error("Validation: %r" % format_exc())
                errors[field.field_name] = exc.detail
            except DjangoValidationError as exc:
                logger.error("DjangoValidation: %r" % format_exc())
                errors[field.field_name] = get_error_detail(exc)
            except SkipField:
                pass
            else:
                source = field.result_source.split('.') if hasattr(field, 'result_source') else field.source_attrs
                set_value(ret, source, validated_value)

        if errors:
            raise ValidationError(errors)

        return ret
