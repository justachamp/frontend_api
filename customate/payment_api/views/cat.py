from django.http import HttpRequest
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

    def get(self, request: HttpRequest):
        """
        HTTP GET /api/v1/cats/

        :param request:
        :return:
        """
        host = request.get_host()
        logger.info("HOST: %s" % host)
        logger.info("MY CATS ARE HERE!!")
        yourdata = [
            {"id": 1, "likes": 10, "comments": 0, "name": "Catty"},
            {"id": 2, "likes": 4, "comments": 23, "name": "My duppa cat"}
        ]
        cats = CatSerializer(data=yourdata, many=True)
        cats.is_valid()
        results = cats.validated_data

        logger.info("CAT RESULTS: %r" % results)
        return Response(results)

    # HTTP/1.1 200 OK
    # {
    #     "data": [
    #         {
    #             "attributes": {
    #                 "comments": 0,
    #                 "likes": 10
    #             },
    #             "id": "None",
    #             "type": "cats"
    #         },
    #         {
    #             "attributes": {
    #                 "comments": 23,
    #                 "likes": 4
    #             },
    #             "id": "None",
    #             "type": "cats"
    #         }
    #     ]
    # }

    def post(self, request):
        logger.info("HERE: %r" % request.data)

        return Response()
