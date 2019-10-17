# -*- coding: utf-8 -*-
import traceback
import logging
import os

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError

from pathlib import Path
import boto3
from botocore.config import Config

from core.models import Model
from frontend_api.models.schedule import Schedule

logger = logging.getLogger(__name__)


class DocumentManager(models.Manager):
    def get_queryset(self):
        """
        Return only documents with 'is_active' fields equal True
        :return:
        """
        return super().get_queryset().filter(is_active=True)


class Document(Model):
    filename = models.CharField(max_length=128)
    # Named as 'key' because for S3 bucket this is the same as filename.
    key = models.CharField(max_length=128, blank=True, null=True, help_text="Unique filename for storing in S3 bucket.")
    slug = models.CharField(max_length=128, blank=True, null=True)
    schedule = models.ForeignKey(Schedule, related_name="documents",
                                 on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(get_user_model(), related_name="schedule_documents",
                             on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)

    objects = DocumentManager()

    def move_to_archive(self) -> None:
        """
        Update field 'is_active' set False value.
        Such documents will be hidden for user.
        :return:
        """
        self.is_active = False
        self.save()

    def save(self, *args, **kwargs):
        # Replace filename with id. Would be as 'c8026b8e-0b61-410b-9e9a-90a6505165e9.jpeg'
        self.key = self.filename.replace(Path(self.filename).stem, str(self.id))
        # Check documents number limit
        if self.schedule:
            if self.schedule.documents.count() >= settings.DOCUMENTS_MAX_LIMIT_PER_SCHEDULE:
                logger.error("Maximum documents per schedule has reached %r" % traceback.format_exc())
                raise ValidationError('Maximum documents limit reached')
        return super().save(*args, **kwargs)

    def generate_s3_presigned_url(self, operation_name: str) -> str:
        """
        Generates presigned URL for HTTP request to AWS
        :param operation_name: 'delete_object', 'get_object', etc.
        :return:
        """
        s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY,
                                 aws_secret_access_key=settings.AWS_SECRET_KEY,
                                 region_name=settings.AWS_REGION,
                                 config=Config(signature_version="s3v4"))

        return s3_client.generate_presigned_url(
            operation_name, Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': os.path.join(settings.AWS_S3_UPLOAD_DOCUMENTS_PATH, self.key)
            },
            ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRES_IN)
