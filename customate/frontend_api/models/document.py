# -*- coding: utf-8 -*-
import traceback
import logging

from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from pytils.translit import slugify

from core.models import Model
from .schedule import Schedule 

logger = logging.getLogger(__name__)


class Document(Model):
	filename = models.CharField(max_length=128, unique=True)
	slug = models.CharField(max_length=128, blank=True, null=True)
	schedule = models.ForeignKey(Schedule, related_name="documents",
								 on_delete=models.CASCADE)
	user = models.ForeignKey(get_user_model(), related_name="schedule_documents",
									on_delete=models.CASCADE)

	def save(self, *args, **kwargs):
		# Make filenames slug
		extension = self.filename.split(".")[-1]
		filename = ".".join(self.filename.split(".")[:-1])
		self.slug = "{}.{}".format(slugify(filename), extension)
		# Chack documents number limit
		if self.schedule.documents.count() >= 4:
			logger.error("Maximum documents per schedule has reached %r" % traceback.format_exc())
			raise ValidationError('Maximum documents limit reached')
		return super().save(*args, **kwargs)