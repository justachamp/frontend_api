from rest_framework_json_api import filters


class BetterQueryParameterValidationFilter(filters.QueryParameterValidationFilter):
    """
    Improved version of QueryParameterValidationFilter, it will skip query parameters validation for POST and PATCH
    request
    """
    def validate_query_params(self, request):
        if request.method in ['PATCH', 'POST']:
            return

        super().validate_query_params(request)

    def filter_queryset(self, request, queryset, view):
        if request.method in ['PATCH', 'POST']:
            return queryset

        return super().filter_queryset(request, queryset, view)
