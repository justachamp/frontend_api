# -*- coding: utf-8 -*-
import traceback
import logging
import os

from django.db import models
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework.exceptions import ValidationError
from pathlib import Path

from core.models import Model
from external_apis.aws.service import get_aws_client
from frontend_api.models import Schedule, Escrow, EscrowStatus
from frontend_api.fields import ScheduleStatus
from core.fields import UserRole

logger = logging.getLogger(__name__)

User = get_user_model()


def get_relation_class(relation_name: str) -> object:
    """
    Dynamically returns relation to Document as class.
    :param relation_name:
    :return:
    """
    if not relation_name:
        raise ValidationError("The 'relation_name' field is required.")
    relation_classes = {
        'schedule': Schedule,
        'escrow': Escrow,
    }
    try:
        relation_class = relation_classes[relation_name]
    except KeyError:
        logger.error("Got invalid relation name: %s. %r" % (relation_name, traceback.format_exc()))
        raise ValidationError("Got invalid relation name.")
    return relation_class


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
    user = models.ForeignKey(User, related_name="user_documents",
                             on_delete=models.CASCADE)
    schedule = models.ForeignKey(Schedule, related_name="documents",
                                 on_delete=models.CASCADE, null=True, blank=True)
    escrow = models.ForeignKey(Escrow, related_name="documents",
                               on_delete=models.CASCADE, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    objects = DocumentManager()

    def get_s3_bucket_path(self, relation_name: str) -> str:
        s3_bucket_paths = {
            'escrow': settings.AWS_S3_UPLOAD_ESCROW_DOCUMENTS_PATH,
            'schedule': settings.AWS_S3_UPLOAD_SCHEDULE_DOCUMENTS_PATH
        }
        try:
            return os.path.join(s3_bucket_paths[relation_name], self.key)
        except KeyError:
            logger.error("Invalid 'relation_name' field has passed to Document.get_s3_bucket_path %r" % traceback.format_exc())
            raise ValidationError("Invalid field 'relation_name'.")

    def move_to_archive(self) -> None:
        """
        Update field 'is_active' set False value.
        Such documents will be hidden for user.
        :return:
        """
        self.is_active = False
        self.save()

    def generate_s3_presigned_url(self, operation_name: str, relation_name: str) -> str:
        """
        Generates presigned URL for HTTP request to AWS
        :param relation_name:
        :param operation_name: 'delete_object', 'get_object', etc.
        :return:
        """
        s3_client = get_aws_client('s3')
        if not relation_name:
            raise ValidationError("The 'relation_name' field is required.")
        return s3_client.generate_presigned_url(
            operation_name, Params={
                'Bucket': settings.AWS_S3_STORAGE_BUCKET_NAME,
                'Key': self.get_s3_bucket_path(relation_name)
            },
            ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRES_IN)

    def allow_get_document(self, user: User) -> bool:
        """
        Check if provided user is able to download particular document.
        :param user:
        :return:
        """
        relation = self.schedule or self.escrow
        # The case where files handling happens on the 'create schedule' page.
        if not relation and self.user == user:
            return True
        recipient = relation.recipient_user
        origin_user = relation.origin_user if isinstance(relation, Schedule) else relation.funder_user
        # Check if user from request is recipient or sender
        if user.role == UserRole.owner:
            return any([recipient == user, origin_user == user])
        # Check if subuser from request is subuser of recipient or sender
        if user.role == UserRole.sub_user:
            return getattr(user.account.permission, "manage_schedules") and \
                   any([recipient == user.account.owner_account.user,
                        origin_user == user.account.owner_account.user,
                        origin_user == user])

    def allow_delete_document(self, user: User) -> bool:
        """
        Check if provided user is able to delete ( move to archive ) particular document.
        :param user:
        :return:
        """
        relation = self.schedule or self.escrow
        if not relation and self.user == user:
            return True
        origin_user = relation.origin_user if isinstance(relation, Schedule) else relation.funder_user
        # Check if schedule has status 'stopped'
        #    need to avoid documents handling for such schedules
        stopped_status = ScheduleStatus.stopped if isinstance(relation, Schedule) else EscrowStatus.stopped
        if relation.status == stopped_status:
            return False
        relation_creator_account = origin_user.account.owner_account if \
            hasattr(origin_user.account, "owner_account") else origin_user.account
        # If document has created by subuser and owner wants to remove it.
        if all([self.user.role == UserRole.sub_user,
                user.role == UserRole.owner]):
            # Check if schedule belongs to user from request
            return all([relation_creator_account == user.account,
                        # And check if subuser is subuser of user from request
                        user.account.sub_user_accounts.filter(user=self.user)])
        return user == self.user

    def save(self, *args, **kwargs):
        # Replace filename with id. Would be as 'c8026b8e-0b61-410b-9e9a-90a6505165e9.jpeg'
        self.key = self.filename.replace(Path(self.filename).stem, str(self.id))
        # Check documents number limit
        if self.schedule:
            if self.schedule.documents.filter(
                    is_active=True).count() > settings.DOCUMENTS_MAX_LIMIT_PER_SCHEDULE:
                logger.error("Maximum documents per schedule has reached %r" % traceback.format_exc())
                raise ValidationError('Maximum documents limit reached')
        if self.escrow:
            if self.escrow.documents.filter(
                    is_active=True).count() > settings.DOCUMENTS_MAX_LIMIT_PER_ESCROW:
                logger.error("Maximum documents per escrow has reached %r" % traceback.format_exc())
                raise ValidationError('Maximum documents limit reached')
        return super().save(*args, **kwargs)
