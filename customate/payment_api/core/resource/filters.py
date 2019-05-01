from rest_framework.compat import (
    coreapi, coreschema
)
from django.utils.functional import cached_property
from rest_framework.filters import BaseFilterBackend, OrderingFilter as BaseOrderingFilter
from rest_framework.exceptions import ValidationError, ParseError
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from rest_framework_json_api.django_filters import DjangoFilterBackend
from rest_framework_json_api.utils import (
    get_included_serializers,
    get_default_included_resources_from_serializer,
)
from inflection import camelize, underscore, singularize


class RQLFilterMixin:
    OPERATORS = {
        'contains': '==*{value}*',
        'startswith': '==*{value}',
        'endswith': '=={value}*',
        'range': '=in=({value})',
        'isnull': '=isnull=',
        'exact': '=={value}',
        'in': '=in=({value})',
        'not_in': '=out=({value})',
        'eq': '=={value}',
        'ne': '!={value}',
        'lte': '<={value}',
        'lt': '<{value}',
        'gte': '>={value}',
        'gt': '>{value}'
    }

    def parse_filter(self, key, value):
        parts = key.split('__')
        parts.insert(0, self.resource)

        if parts[-1] in self.OPERATORS.keys():
            value = self.OPERATORS[parts[-1]].format(value=value)
            parts = parts[:-1]
        else:
            value = f'=={value}'

        if len(parts) > 1:
            field_parts = [camelize(part, False) for part in parts[1:]]
            value = f'{".".join(field_parts)}{value}'

        key = f'[{parts[0]}]='

        return {key: value}

    def parse_value(self, filters, key, value):
        if isinstance(value, dict) and value.get('method'):
            fn = getattr(self._view, value.get('method'))
            value = fn(filters, key, value)
            if value is not None:
                return {key: value}
        else:
            return {key: value}


class RQLFilterSet(RQLFilterMixin):

    def __init__(self, filter_data, view, queryset, request, base_filters):
        self._filter_data = filter_data
        self._view = view
        self._queryset = queryset
        self._request = request
        self.base_filters = self._initiate_base_filters(base_filters if isinstance(base_filters, dict) else {})

    @cached_property
    def resource(self):
        return self._view.external_resource_name

    def _initiate_base_filters(self, base_filters_config):
        base_filters = {}
        for filter_name, filter_parts in base_filters_config.items():
            base_filters.update({f'{filter_name}__{filter_part}': filter_part for filter_part in filter_parts})
        return base_filters

    @cached_property
    def filter_data(self):
        filter_data = self._filter_data.get('data', {})
        meta = getattr(self._view, 'Meta', None)
        filters = getattr(meta, 'filters', None)
        if filters:
            for filter_obj in filters:
                filter_data.update(filter_obj)

        return filter_data

    @property
    def qs(self):
        queryset = self._queryset
        filters = self.filters
        if filters:
            queryset.filter = filters

        return queryset

    @cached_property
    def filters(self):
        filters = {}
        data = self.filter_data
        for filter_name in self.base_filters:
            if filter_name in data.keys():
                value = self.parse_value(filters, filter_name, data.get(filter_name))

                if isinstance(value, dict) and filter_name in value:
                    filter_data = self.parse_filter(filter_name, value.get(filter_name))
                    key = next(iter(filter_data))

                    if filters.get(key, None):
                        if isinstance(filters[key], list):
                            filters[key].append(filter_data[key])
                        else:
                            filters[key] = [filters[key], filter_data[key]]
                    else:
                        filters.update(filter_data)

        return filters


class ResourceFilterBackend(DjangoFilterBackend):

    def filter_queryset(self, request, queryset, view):
        data = self.get_filterset_kwargs(request, queryset, view)
        #TODO add filtermapping
        filter_set = RQLFilterSet(data, view, queryset, request, base_filters=getattr(view, 'filterset_fields', None))

        self._validate_filter(data.pop('filter_keys'), filter_set)

        return filter_set.qs

    def _validate_filter(self, keys, filterset_class):
        """
        Check that all the filter[key] are valid.

        :param keys: list of FilterSet keys
        :param filterset_class: :py:class:`django_filters.rest_framework.FilterSet`
        :raises ValidationError: if key not in FilterSet keys or no FilterSet.
        """
        for k in keys:
            if not filterset_class or k not in filterset_class.base_filters:
                raise ValidationError("invalid filter[{}]".format(k))

    def get_filterset(self, *args, **kwargs):
        return None


class InclusionFiler(BaseFilterBackend):
    """
    A backend filter that implements https://jsonapi.org/format/#fetching-includes and
    raises a 400 error if any related field is invalid.
    """
    #: override :py:attr:`payment_api.core.resource.filers.IncludingFilter.including_param`
    #: with JSON:API-compliant query parameter name.
    inclusion_param = 'include'
    inclusion_title = _('Inclusion')
    inclusion_description = _('Inclusion')

    def filter_queryset(self, request, queryset, view):
        # inclusion = self.get_inclusion(request, queryset, view)
        serializer = view.get_serializer_class()
        included_resources = self.get_included_resources(request, serializer)

        inclusion = self.prepare_inclusion(serializer, included_resources)

        if inclusion:
            return queryset.including(*inclusion)

        return queryset

    def get_inclusion(self, request, serializer):
        """
        Including is set by a comma delimited ?included=... query parameter.
        """
        params = request.query_params.get(self.inclusion_param)
        including = [param.strip() for param in params.split(',')] if params else None
        meta_including = getattr(serializer.Meta, 'include_resources', None) if (serializer and
                                                                                 hasattr(serializer, 'Meta')) else None
        if meta_including:
            including = including + meta_including if including else meta_including
        return including

    def get_included_resources(self, request, serializer=None):
        """ Build a list of included resources. """
        include_resources_param = self.get_inclusion(request, serializer)

        if include_resources_param:
            return include_resources_param
        else:
            return get_default_included_resources_from_serializer(serializer)

    def prepare_inclusion(self, serializer_class, included_resources):
        prepared_resources = []

        def get_serializer_resource(serializer, inclusion):
            meta = getattr(serializer, 'Meta')
            if meta:
                external_resource_name = getattr(meta, 'external_resource_name', None)
                resource_name = getattr(meta, 'resource_name', None)
                if external_resource_name and resource_name:
                    return inclusion.replace(singularize(resource_name), singularize(external_resource_name))

            return inclusion

        def inclusion_mapping(serializer_cls, field_path, path):
            mapped_fields = []
            serializers = get_included_serializers(serializer_cls)
            if serializers is None:
                raise ParseError('This endpoint does not support the include parameter')
            this_field_name = underscore(field_path[0])
            this_included_serializer = serializers.get(this_field_name)
            if this_included_serializer is None:
                raise ParseError(
                    'This endpoint does not support the include parameter for path {}'.format(
                        path
                    )
                )
            if len(field_path) > 1:
                new_included_field_path = field_path[1:]
                # We go down one level in the path
                mapped_fields.extend(inclusion_mapping(this_included_serializer, new_included_field_path, path))

            mapped_fields.insert(0, get_serializer_resource(this_included_serializer, field_path[0]))
            return mapped_fields

        for included_field_name in included_resources:
            included_field_path = included_field_name.split('.')
            inclu = inclusion_mapping(serializer_class, included_field_path, included_field_name)
            prepared_resources.append('.'.join(inclu))

        return prepared_resources

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
        assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'
        return [
            coreapi.Field(
                name=self.inclusion_param,
                required=False,
                location='query',
                schema=coreschema.String(
                    title=force_text(self.inclusion_title),
                    description=force_text(self.inclusion_description)
                )
            )
        ]


class OrderingFilter(BaseOrderingFilter):

    def get_ordering(self, request, queryset, view):
        """
        Ordering is set by a comma delimited ?ordering=... query parameter.

        The `ordering` query parameter can be overridden by setting
        the `ordering_param` value on the OrderingFilter or by
        specifying an `ORDERING_PARAM` value in the API settings.
        """
        params = request.query_params.get(self.ordering_param)
        if params:
            fields = [camelize(param.strip(), False) for param in params.split(',')]
            ordering = self.remove_invalid_fields(queryset, fields, view, request)
            if ordering:
                return ordering

        # No ordering was included, or all the ordering fields were invalid
        return self.get_default_ordering(view)

    def remove_invalid_fields(self, queryset, fields, view, request):
        """
        Extend :py:meth:`rest_framework.filters.OrderingFilter.remove_invalid_fields` to
        validate that all provided sort fields exist (as contrasted with the super's behavior
        which is to silently remove invalid fields).

        :raises ValidationError: if a sort field is invalid.
        """
        valid_fields = [
            item[0] for item in self.get_valid_fields(queryset, view,
                                                      {'request': request})
        ]
        bad_terms = [
            term for term in fields if term.lstrip('-') not in valid_fields
        ]

        if bad_terms:
            raise ValidationError('invalid sort parameter{}: {}'.format(
                ('s' if len(bad_terms) > 1 else ''), ','.join(bad_terms)))
        # this looks like it duplicates code above, but we want the ValidationError to report
        # the actual parameter supplied while we want the fields passed to the super() to
        # be correctly rewritten.
        # The leading `-` has to be stripped to prevent format_value from turning it into `_`.
        camelize_fields = []
        for item in fields:
            item_rewritten = item.replace(".", "__")
            if item_rewritten.startswith('-'):
                camelize_fields.append('-' + camelize(item_rewritten.lstrip('-'), False))
            else:
                camelize_fields.append(camelize(item_rewritten, False))

        return super(OrderingFilter, self).remove_invalid_fields(
            queryset, camelize_fields, view, request)


class IbanGeneralPartFiler(BaseFilterBackend):

    iban_param = 'ibanGeneralPart'
    iban_title = _('IBAN general part')
    iban_description = _('IBAN general part')

    def filter_queryset(self, request, queryset, view):
        iban = self.get_iban_general_part(request, queryset, view)

        if iban:
            queryset.modifier = f'ibanGeneralPart={iban}'
        return queryset

    def get_iban_general_part(self, request, queryset, view):
        """
        Including is set by a comma delimited ?included=... query parameter.
        """
        param = request.query_params.get(self.iban_param)
        iban = param.strip() if param else None
        return iban

    def get_schema_fields(self, view):
        assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
        assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'
        return [
            coreapi.Field(
                name=self.iban_param,
                required=False,
                location='query',
                schema=coreschema.String(
                    title=force_text(self.iban_title),
                    description=force_text(self.iban_description)
                )
            )
        ]