from rest_framework_json_api.views import viewsets
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework import response
from core.fields import Dataset


class DatasetView(viewsets.ViewSet):

    permission_classes = ()

    @action(methods=['GET'], detail=False)
    def all(self, request):
        return response.Response(Dataset.all())
