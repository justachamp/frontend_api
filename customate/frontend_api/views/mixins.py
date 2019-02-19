from collections import Iterable
from django.db import transaction
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed
from rest_framework.exceptions import NotFound

import logging

logger = logging.getLogger(__name__)


class PatchRelatedMixin(object):
    def patch_related(self, request, *args, **kwargs):
        serializer_kwargs = {}
        instance = self.get_related_instance()

        if hasattr(instance, 'all'):
            instance = instance.all()

        if callable(instance):
            instance = instance()

        if instance is None:
            return Response(data=None)

        if isinstance(instance, Iterable):
            serializer_kwargs['many'] = True
        serializer_kwargs['data'] = request.data

        serializer = self.get_serializer(instance, **serializer_kwargs)
        serializer.is_valid(True)
        serializer.save()
        return Response(serializer.data)


class RelationshipMixin(object):
    _related_serializers = {}

    def get_related_serializer(self, serializer_name):
        return self._related_serializers.get(serializer_name) if serializer_name in self._related_serializers else None


class RelationshipPostMixin(RelationshipMixin):

    def get_related_handler(self, releted_field):
        try:
            return getattr(self, f'post_{releted_field}')
        except AttributeError:
            raise NotFound

    @transaction.atomic()
    def post(self, request, *args, **kwargs):
        related_field = kwargs.get('related_field')
        related_serializer = self.get_related_serializer(related_field)
        if related_serializer:
            handler = self.get_related_handler(related_field)
            serializer = handler(request, *args, **kwargs)

            return Response(serializer.data)
        else:
            raise MethodNotAllowed('POST')
