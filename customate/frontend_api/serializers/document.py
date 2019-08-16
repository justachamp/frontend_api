# -*- coding: utf-8 -*-
from rest_framework_json_api.serializers import ModelSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model

from frontend_api.models import Document, Schedule 

from core.fields import UserRole


class DocumentSerializer(ModelSerializer):

	class Meta:
		model = Document 
		fields = ("id", "slug", "schedule", "user")
		extra_kwargs = {
			"schedule": {"write_only": True},
			"user": {"write_only": True}
		}

	def has_delete_permission(self, instance):
		"""
		Detects if user from request has permissions for removing document
		"""
		user = self.context["request"].user
		schedule_creator_account = instance.schedule.user.account.owner_account if \
		                            hasattr(instance.schedule.user.account, "owner_account") else \
		                             instance.schedule.user.account  
		# If document has created by subuser and owner wants to remove it.
		if all([ instance.user.role == UserRole.sub_user,   
		         user.role == UserRole.owner ]):    
		                # Check if schedule belongs to user from request
		    return all([schedule_creator_account == user.account,   
		                # And check if subuser is subuser of user from request
		                user.account.sub_user_accounts.filter(user=instance.user)])  
		return user == instance.user

	def to_representation(self, instance):
		"""
		Assign 'delete' key to response which is boolean.
		"""
		data = super().to_representation(instance)
		data["delete"] = self.has_delete_permission(instance)
		return data
