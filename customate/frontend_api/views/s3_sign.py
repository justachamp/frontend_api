# -*- coding: utf-8 -*-
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

    def get_s3_object(self, request):
        """
        The method returns presigned url for further sharing file
        """
        key = request.query_params.get("key")
        logger.info("Receiving S3 object by key (key=%s)" % key)

        if not key:
            logger.error("The 'key' parameter has not been passed %r" % traceback.format_exc())
            raise ValidationError("The 'key' field is requred.")
        document = get_object_or_404(Document, key=key)
        try:
            response = document.generate_s3_presigned_url(operation_name="get_object")
            return {"attributes": {"url": response}}
        except ClientError as e:
            logger.error("AWS S3 service is unailable %r" % traceback.format_exc())
            raise ServiceUnavailable

    def post_s3_object(self, request):
        """
        The method returns presigned url for further posting object to S3
        """
        schedule_id = request.query_params.get("schedule_id")
        filename = request.query_params.get("filename")
        slug = request.query_params.get("slug")

        logger.info("Creating S3 object (schedule_id=%s, filename=%s, slug=%s)" % (schedule_id, filename, slug))
        schedule = get_object_or_404(Schedule, id=schedule_id) if schedule_id else None
        kwargs = {"filename": filename, "slug": slug, "user": request.user}
        if schedule:
            kwargs.update({"schedule": schedule})
        # Create a new document.
        # Need to validate filename and maximum documents limit
        document = Document.objects.create(**kwargs)
        # Request to aws
        try:
            response = self.s3_client.generate_presigned_post(
                settings.AWS_S3_STORAGE_BUCKET_NAME,
                os.path.join(settings.AWS_S3_UPLOAD_DOCUMENTS_PATH, document.key),
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
