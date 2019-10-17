# -*- coding: utf-8 -*-
from rest_framework_json_api.serializers import ModelSerializer


from frontend_api.fields import SchedulePurpose
from frontend_api.models import Document
from core.fields import UserRole


class DocumentSerializer(ModelSerializer):
    class Meta:
        model = Document
        fields = ("slug", "key", "schedule", "user")
        extra_kwargs = {
            "schedule": {"write_only": True},
            "user": {"write_only": True},
            "id": {"validators": []}
        }

    def has_delete_permission(self, instance):
        """
        Detects if user from request has permissions for removing document
        """
        user = self.context["request"].user
        if not instance.schedule and instance.user == user:
            return True
        schedule_creator_user = instance.schedule.origin_user if \
            instance.schedule.purpose == SchedulePurpose.pay else \
            instance.schedule.recipient_user
        schedule_creator_account = schedule_creator_user.account.owner_account if \
            hasattr(schedule_creator_user.account, "owner_account") else \
            schedule_creator_user.account
        # If document has created by subuser and owner wants to remove it.
        if all([instance.user.role == UserRole.sub_user,
                user.role == UserRole.owner]):
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
