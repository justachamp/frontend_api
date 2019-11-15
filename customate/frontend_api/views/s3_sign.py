# -*- coding: utf-8 -*-
from typing import Dict
import logging
import traceback
import os

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.shortcuts import get_object_or_404
from botocore.exceptions import ClientError
from external_apis.aws.service import get_aws_client
from frontend_api.serializers import DocumentSerializer
from frontend_api.models import Schedule, Document
from frontend_api.exceptions import ServiceUnavailable
from frontend_api.permissions import (
    HasParticularDocumentPermission,
    IsActive,
    IsOwnerOrReadOnly,
    SubUserManageSchedulesPermission,
)

logger = logging.getLogger(__name__)


class PreSignedUrlView(APIView):
    """
    APIView returns S3 presigned urls for handling files.
    """
    permission_classes = (
        IsAuthenticated,
        IsActive,
        IsOwnerOrReadOnly |
        SubUserManageSchedulesPermission,
        HasParticularDocumentPermission
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.s3_client = get_aws_client('s3')

    def get_relation_class(self, relation_name: str) -> object:
        """
        Dynamically returns relation to Document as class.
        :param relation_name:
        :return:
        """
        if not relation_name:
            raise ValidationError("The 'relation_name' field is required.")
        relation_classes = {
            'schedule': Schedule
         }
        try:
            relation_class = relation_classes[relation_name]
        except KeyError:
            logger.error("Got invalid relation name: %s. %r" % (relation_name, traceback.format_exc()))
            raise ValidationError("Got invalid relation name.")
        return relation_class

    def get_document_path(self, relation_class: object, key: str) -> str:
        """
        Dynamically returns upload path at S3 bucket for document.
        :param relation_class:
        :param key:
        :return:
        """
        return {
            Schedule: os.path.join(settings.AWS_S3_UPLOAD_SCHEDULE_DOCUMENTS_PATH, key)
        }[relation_class]

    def get_s3_object(self, request) -> Dict:
        """
        The method returns presigned url for further sharing file
        """
        key = request.query_params.get("key")
        logger.info("Receiving S3 object by key (key=%s)" % key)

        if not key:
            logger.error("The 'key' parameter has not been passed %r" % traceback.format_exc())
            raise ValidationError("The 'key' field is required.")
        document = get_object_or_404(Document, key=key)
        try:
            response = document.generate_s3_presigned_url(operation_name="get_object")
            return {"attributes": {"url": response}}
        except ClientError as e:
            logger.error("AWS S3 service is unavailable %r" % traceback.format_exc())
            raise ServiceUnavailable

    def post_s3_object(self, request) -> Dict:
        """
        The method returns presigned url for further posting object to S3
        """
        relation_id = request.query_params.get("relation_id")
        relation_name = request.query_params.get("relation_name")
        filename = request.query_params.get("filename")
        slug = request.query_params.get("slug")

        model_fields = {
            "filename": filename,
            "slug": slug,
            "user": request.user
        }
        relation_class = self.get_relation_class(relation_name)
        if relation_id:
            relation_obj = get_object_or_404(relation_class, id=relation_id)
            model_fields.update({relation_name: relation_obj})

        # Create new document. Need to validate maximum documents limit
        document = Document.objects.create(**model_fields)
        # Request to aws
        try:
            response = self.s3_client.generate_presigned_post(
                settings.AWS_S3_STORAGE_BUCKET_NAME,
                self.get_document_path(relation_class, document.key),
                ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRES_IN)
        except ClientError as e:
            logger.error("AWS S3 service is unavailable %r" % traceback.format_exc())
            raise ServiceUnavailable
        serializer = DocumentSerializer(document, context={"request": request})
        return {"meta": serializer.data, "attributes": response}

    def get(self, request):
        method_name = request.query_params.get("method_name")
        logger.info("Handle S3 object processing request (method_name=%s)" % method_name)

        try:
            if method_name not in ["get_s3_object", "post_s3_object"]:
                raise AttributeError()
            response = getattr(self, method_name)(request)
        except AttributeError as e:
            logger.error("Got unrecognized method name %r" % traceback.format_exc())
            raise ValidationError("Unrecognized method: {}".format(method_name))
        return Response(response)
