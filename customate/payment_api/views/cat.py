from rest_framework.permissions import AllowAny
from rest_framework import views
from rest_framework.response import Response

from ..serializers.cat import CatSerializer

import logging

logger = logging.getLogger(__name__)


class CatView(views.APIView):
    """
    Sample dummy view to test DRF without specific models.
    Inspired by https://medium.com/django-rest-framework/django-rest-framework-viewset-when-you-don-t-have-a-model-335a0490ba6f

    https://github.com/linovia/drf-demo

    """
    permission_classes = (AllowAny,)
    resource_name = 'cats'

    # ['get', 'post', 'put', 'patch', 'delete', 'head', 'options', 'trace']

    def get(self, request):
        logger.info("MY CATS ARE HERE!!")
        yourdata = [{"id": 1, "likes": 10, "comments": 0}, {"id": 2, "likes": 4, "comments": 23}]
        results = CatSerializer(yourdata, many=True).data
        logger.info("CAT RESULTS: %r" % results)
        return Response(results)

    def post(self, request):
        logger.info("HERE: %r" % request.data)

        return Response()
