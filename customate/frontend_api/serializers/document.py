# -*- coding: utf-8 -*-
from rest_framework_json_api.serializers import ModelSerializer
from frontend_api.models import Document


class DocumentSerializer(ModelSerializer):
    class Meta:
        model = Document
        fields = ("slug", "key", "schedule", "escrow", "user")
        extra_kwargs = {
            "schedule": {"write_only": True},
            "escrow": {"write_only": True},
            "user": {"write_only": True},
            "id": {"validators": []}
        }

    def to_representation(self, instance):
        """
        Assign 'delete' key to response which is boolean.
        :param instance:
        :return:
        """
        user = self.context["request"].user
        data = super().to_representation(instance)
        data["delete"] = instance.allow_delete_document(user)
        return data

