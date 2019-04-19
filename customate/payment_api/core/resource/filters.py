from rest_framework.compat import (
    coreapi, coreschema
)
from django.utils.functional import cached_property
from rest_framework.filters import BaseFilterBackend
from rest_framework.exceptions import ValidationError
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _
from rest_framework_json_api.django_filters import DjangoFilterBackend
from rest_framework_json_api.utils import format_field_names


class RQLFilterSet:
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
                filter_data = self.parse_filter(filter_name, data.get(filter_name))
                key = next(iter(filter_data))
                if filters.get(key, None):
                    if isinstance(filters[key], list):
                        filters[key].append(filter_data[key])
                    else:
                        filters[key] = [filters[key], filter_data[key]]
                else:
                    filters.update(filter_data)

        return filters

    def parse_filter(self, key, value):
        parts = key.split('__')
        parts.insert(0, self.resource)

        if parts[-1] in self.OPERATORS.keys():
            value = self.OPERATORS[parts[-1]].format(value=value)
            parts = parts[:-1]
        else:
            value = f'=={value}'

        if len(parts) > 1:
            field_parts = [next(iter(format_field_names({part: part}, format_type='camelize'))) for part in parts[1:]]
            value = f'{".".join(field_parts)}{value}'

        key = f'[{parts[0]}]='

        return {key: value}


class ResourceFilterBackend(DjangoFilterBackend):

    def filter_queryset(self, request, queryset, view):
        data = self.get_filterset_kwargs(request, queryset, view)
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
        inclusion = self.get_inclusion(request, queryset, view)

        if inclusion:
            return queryset.including(*inclusion)

        return queryset

    def get_inclusion(self, request, queryset, view):
        """
        Including is set by a comma delimited ?included=... query parameter.
        """
        params = request.query_params.get(self.inclusion_param)
        including = [param.strip() for param in params.split(',')] if params else None
        meta_including = getattr(view.Meta, 'include_resources', None) if hasattr(view, 'Meta') else None
        if meta_including:
            including = including + meta_including if including else meta_including
        return including

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