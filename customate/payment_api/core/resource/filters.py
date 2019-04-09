from rest_framework.compat import (
    coreapi, coreschema
)
from rest_framework.filters import BaseFilterBackend
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

# class ResourceFilterBackend:
#     """
#     A Django-style ORM filter implementation, using `django-filter`.
#
#     This is not part of the jsonapi standard per-se, other than the requirement
#     to use the `filter` keyword: This is an optional implementation of style of
#     filtering in which each filter is an ORM expression as implemented by
#     DjangoFilterBackend and seems to be in alignment with an interpretation of
#     http://jsonapi.org/recommendations/#filtering, including relationship
#     chaining. It also returns a 400 error for invalid filters.
#
#     Filters can be:
#
#     - A resource field
#       equality test:
#
#       ``?filter[qty]=123``
#
#     - Apply other
#       https://docs.djangoproject.com/en/stable/ref/models/querysets/#field-lookups
#       operators:
#
#       ``?filter[name.icontains]=bar`` or ``?filter[name.isnull]=true...``
#
#     - Membership in
#       a list of values:
#
#       ``?filter[name.in]=abc,123,zzz`` (name in ['abc','123','zzz'])
#
#     - Filters can be combined
#       for intersection (AND):
#
#       ``?filter[qty]=123&filter[name.in]=abc,123,zzz&filter[...]``
#
#     - A related resource path
#       can be used:
#
#       ``?filter[inventory.item.partNum]=123456`` (where `inventory.item` is the relationship path)
#
#     If you are also using rest_framework.filters.SearchFilter you'll want to customize
#     the name of the query parameter for searching to make sure it doesn't conflict
#     with a field name defined in the filterset.
#     The recommended value is: `search_param="filter[search]"` but just make sure it's
#     `filter[<something>]` to comply with the jsonapi spec requirement to use the filter
#     keyword. The default is "search" unless overriden but it's used here just to make sure
#     we don't complain about it being an invalid filter.
#     """
#     search_param = api_settings.SEARCH_PARAM
#
#     # Make this regex check for 'filter' as well as 'filter[...]'
#     # See http://jsonapi.org/format/#document-member-names for allowed characters
#     # and http://jsonapi.org/format/#document-member-names-reserved-characters for reserved
#     # characters (for use in paths, lists or as delimiters).
#     # regex `\w` matches [a-zA-Z0-9_].
#     # TODO: U+0080 and above allowed but not recommended. Leave them out for now.e
#     #       Also, ' ' (space) is allowed within a member name but not recommended.
#     filter_regex = re.compile(r'^filter(?P<ldelim>\[?)(?P<assoc>[\w\.\-]*)(?P<rdelim>\]?$)')
#
#     def _validate_filter(self, keys, filterset_class):
#         """
#         Check that all the filter[key] are valid.
#
#         :param keys: list of FilterSet keys
#         :param filterset_class: :py:class:`django_filters.rest_framework.FilterSet`
#         :raises ValidationError: if key not in FilterSet keys or no FilterSet.
#         """
#         for k in keys:
#             if ((not filterset_class) or (k not in filterset_class.base_filters)):
#                 raise ValidationError("invalid filter[{}]".format(k))
#
#     def get_filterset(self, request, queryset, view):
#         """
#         Sometimes there's no `filterset_class` defined yet the client still
#         requests a filter. Make sure they see an error too. This means
#         we have to `get_filterset_kwargs()` even if there's no `filterset_class`.
#         """
#         # TODO: .base_filters vs. .filters attr (not always present)
#         filterset_class = self.get_filterset_class(view, queryset)
#         kwargs = self.get_filterset_kwargs(request, queryset, view)
#         self._validate_filter(kwargs.pop('filter_keys'), filterset_class)
#         if filterset_class is None:
#             return None
#         return filterset_class(**kwargs)
#
#     def get_filterset_kwargs(self, request, queryset, view):
#         """
#         Turns filter[<field>]=<value> into <field>=<value> which is what
#         DjangoFilterBackend expects
#
#         :raises ValidationError: for bad filter syntax
#         """
#         filter_keys = []
#         # rewrite filter[field] query params to make DjangoFilterBackend work.
#         data = request.query_params.copy()
#         for qp, val in data.items():
#             m = self.filter_regex.match(qp)
#             if m and (not m.groupdict()['assoc'] or
#                       m.groupdict()['ldelim'] != '[' or m.groupdict()['rdelim'] != ']'):
#                 raise ValidationError("invalid query parameter: {}".format(qp))
#             if m and qp != self.search_param:
#                 if not val:
#                     raise ValidationError("missing {} test value".format(qp))
#                 # convert jsonapi relationship path to Django ORM's __ notation
#                 key = m.groupdict()['assoc'].replace('.', '__')
#                 # undo JSON_API_FORMAT_FIELD_NAMES conversion:
#                 key = format_value(key, 'underscore')
#                 data[key] = val
#                 filter_keys.append(key)
#                 del data[qp]
#         return {
#             'data': data,
#             'queryset': queryset,
#             'request': request,
#             'filter_keys': filter_keys,
#         }
#
#     def filter_queryset(self, request, queryset, view):
#         """
#         This is backwards compatibility to django-filter 1.1 (required for Python 2.7).
#         In 1.1 `filter_queryset` does not call `get_filterset` or `get_filterset_kwargs`.
#         """
#         # TODO: remove when Python 2.7 support is deprecated
#         if VERSION >= (2, 0, 0):
#             return super(DjangoFilterBackend, self).filter_queryset(request, queryset, view)
#
#         filter_class = self.get_filter_class(view, queryset)
#
#         kwargs = self.get_filterset_kwargs(request, queryset, view)
#         self._validate_filter(kwargs.pop('filter_keys'), filter_class)
#
#         if filter_class:
#             return filter_class(kwargs['data'], queryset=queryset, request=request).qs
#
#         return queryset
#
# # django_filters.DjangoFilterBackend
# """
# A base class from which all filter backend classes should inherit.
# """
#
#
# def filter_queryset(self, request, queryset, view):
#     """
#     Return a filtered queryset.
#     """
#     raise NotImplementedError(".filter_queryset() must be overridden.")
#
#
# def get_schema_fields(self, view):
#     assert coreapi is not None, 'coreapi must be installed to use `get_schema_fields()`'
#     assert coreschema is not None, 'coreschema must be installed to use `get_schema_fields()`'
#     return []


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