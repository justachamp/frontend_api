
import json
from uuid import UUID
import logging
import traceback

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.db import IntegrityError

import boto3
from botocore.exceptions import ClientError

from frontend_api.serializers import DocumentSerializer
from frontend_api.models import Schedule, Document 
from frontend_api.exceptions import ServiceUnavailable
from frontend_api.permissions import ( 
    HasParticularDocumentPermission,
    IsActive,
    SubUserManageSchedulesPermission )
from .mixins import PatchRelatedMixin, RelationshipMixin, RelationshipPostMixin
from .account import (
    AccountRelationshipView,
    AccountViewSet,
    UserAccountViewSet,
    AdminUserAccountViewSet,
    SubUserAccountViewSet,
    UserAccountRelationshipView,
    AdminUserAccountRelationshipView,
    SubUserAccountRelationshipView
)
from .dataset import DatasetView
from .address import UserAddressViewSet, AddressViewSet, CompanyAddressViewSet, AddressRelationshipView
from .company import CompanyRelationshipView, CompanyViewSet
from .permission import (
    SubUserPermissionViewSet,
    AdminUserPermissionViewSet,
    SubUserPermissionRelationshipView,
    AdminUserPermissionRelationshipView
)
from .shareholder import ShareholderRelationshipView, ShareholderViewSet
from .user import AdminUserViewSet, UserViewSet, UserRelationshipView
from .profile import ProfileView
from .schedule import ScheduleViewSet

logger = logging.getLogger(__name__)


class PreSignedUrlView(APIView):
    """
    APIView returns S3 presigned urls for handling files.
    """
    permission_classes = (
            IsAuthenticated,
            IsActive,
            HasParticularDocumentPermission )

    def __init__(self, *args, **kwargs):
        self.s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY,
                                       aws_secret_access_key=settings.AWS_SECRET_KEY, 
                                       region_name=settings.AWS_REGION)

    def get_s3_object(self, request):
        """
        The method returns presigned url for further sharing file
        """
        document_id = request.query_params.get("document_id")
        document = get_object_or_404(Document, id=UUID(document_id))
        try:
            response = self.s3_client.generate_presigned_url(
                            'get_object',
                            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                                    'Key': document.slug},
                            ExpiresIn=settings.AWS_S3_EXPIRE_PRESIGNED_URL)
            return {"url": response}
        except ClientError as e:
            logger.error("AWS S3 service is unailable %r" % traceback.format_exc())
            raise ServiceUnavailable

    def post_s3_object(self, request):
        """
        The method returns presigned url for further posting object to S3
        """
        schedule_id = request.query_params.get("schedule_id")
        schedule = get_object_or_404(Schedule, id=UUID(schedule_id))

        # Create a new document.
        # Need to validate filename and maximum documents limit 
        try:
            filename = request.query_params.get("filename")
            document = Document.objects.create(schedule=schedule, 
                                               filename=filename,
                                               user=request.user)
        except IntegrityError:
            logger.error("Got duplicate file name %r" % traceback.format_exc())
            raise ValidationError("Duplicate file name. Please choose another one.")
    
        # Request to aws
        try:
            response = self.s3_client.generate_presigned_post(
                                            settings.AWS_STORAGE_BUCKET_NAME,
                                            document.slug,
                                            ExpiresIn=settings.AWS_S3_EXPIRE_PRESIGNED_URL)
        except ClientError as e:
            logger.error("AWS S3 service is unavailable %r" % traceback.format_exc())
            raise ServiceUnavailable
        serializer = DocumentSerializer(document, context={"request":request})
        return {**serializer.data, "presigned_data": response}

    def delete_s3_object(self, request):
        """
        The method returns presigned url for further sharing file
        """
        document_id = request.query_params.get("document_id")
        document = get_object_or_404(Document, id=document_id)
        try:
            response = self.s3_client.generate_presigned_url(
                                            'delete_object',
                                            Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                                                    'Key': document.slug},
                                            ExpiresIn=settings.AWS_S3_EXPIRE_PRESIGNED_URL)
            return {"url": response}
        except ClientError as e:
            logger.error("AWS S3 service is unailable %r" % traceback.format_exc())
            raise ServiceUnavailable

    def get(self, request):
        method_name = request.query_params.get("method_name")
        try:
            response = getattr(self, method_name)(request)
        except AttributeError as e:
            logger.error("Got unrecognized method name %r" % traceback.format_exc())
            raise ValidationError("Unrecognized method: {}".format(method_name))
        return Response(response)



__all__ = [
    PatchRelatedMixin,
    RelationshipMixin,
    RelationshipPostMixin,
    AccountRelationshipView,
    AccountViewSet,
    UserAccountViewSet,
    AdminUserAccountViewSet,
    SubUserAccountViewSet,
    UserAccountRelationshipView,
    AdminUserAccountRelationshipView,
    SubUserAccountRelationshipView,
    UserAddressViewSet,
    AddressViewSet,
    CompanyAddressViewSet,
    AddressRelationshipView,
    SubUserPermissionViewSet,
    AdminUserPermissionViewSet,
    SubUserPermissionRelationshipView,
    AdminUserPermissionRelationshipView,
    ShareholderRelationshipView,
    ShareholderViewSet,
    AdminUserViewSet,
    UserViewSet,
    DatasetView,
    UserRelationshipView,
    CompanyRelationshipView,
    CompanyViewSet,
    ProfileView,
    ScheduleViewSet,
    PreSignedUrlView
]
