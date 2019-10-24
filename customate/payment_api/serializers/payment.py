from uuid import uuid4
from django.contrib.auth import get_user_model

from payment_api.serializers import (
    UUIDField,
    CharField,
    Currency,
    EnumField,
    PaymentScenario,
    LoadFundsPaymentType,
    PaymentStatusType,
    ResourceMeta,
    JSONField,
    TimestampField,
    ResourceSerializer,
    ExternalResourceRelatedField
)
from frontend_api import helpers
from frontend_api.tasks.notifiers import send_notification_email, send_notification_sms
from core.fields import PaymentStatusType


class LoadFundsSerializer(ResourceSerializer):
    included_serializers = {
        'transactions': 'payment_api.serializers.TransactionSerializer',
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer',
        'origin': 'payment_api.serializers.FundingSourceSerializer',
        'recipient': 'payment_api.serializers.PayeeSerializer',
    }

    # @NOTE: Cannot use just uuid as default value (issue with JSON serialization)
    id = UUIDField(default=lambda: str(uuid4()))
    schedule_id = UUIDField(source='scheduleId', required=False)
    creation_date = TimestampField(read_only=True, source='creationDate')
    currency = EnumField(enum=Currency, primitive_value=True)
    scenario = EnumField(enum=LoadFundsPaymentType, primitive_value=True)

    status = EnumField(enum=PaymentStatusType, primitive_value=True, read_only=True),
    update_date = TimestampField(read_only=True, source='updateDate'),
    user_id = UUIDField(source='userId', read_only=True)
    data = JSONField(required=True)
    transactions = ExternalResourceRelatedField(
        many=True,
        required=False,
        read_only=True,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
    )

    payment_account = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
        source='account'
    )

    origin = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships'
    )

    recipient = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships'
    )

    def validate(self, attrs):
        self.service.prepare_funds(attrs)
        return attrs

    class Meta(ResourceMeta):
        service = 'payment_api.services.FundsRequestResourceService'
        resource_name = 'funds'
        external_resource_name = 'payments'


class MakePaymentSerializer(ResourceSerializer):
    included_serializers = {
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer',
        'origin': 'payment_api.serializers.FundingSourceSerializer',
        'recipient': 'payment_api.serializers.PayeeSerializer',
    }

    id = CharField(default=lambda: str(uuid4()))  # @NOTE: doesn't work with UUIDField
    status = EnumField(enum=PaymentStatusType, primitive_value=True, read_only=True)
    schedule_id = CharField(source='scheduleId', required=True)  # @NOTE: doesn't work with UUIDField
    currency = EnumField(enum=Currency, primitive_value=True)
    user_id = CharField(source='userId', required=True)  # @NOTE: doesn't work with UUIDField
    data = JSONField(required=True)

    payment_account = ExternalResourceRelatedField(
        required=True,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
        source='account'
    )

    origin = ExternalResourceRelatedField(
        required=True,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships'
    )

    recipient = ExternalResourceRelatedField(
        required=True,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships'
    )

    class Meta(ResourceMeta):
        resource_name = 'payments'


class PaymentSerializer(ResourceSerializer):
    included_serializers = {
        'transactions': 'payment_api.serializers.TransactionSerializer',
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer',
        'origin': 'payment_api.serializers.FundingSourceSerializer',
        'recipient': 'payment_api.serializers.PayeeSerializer',
    }

    id = UUIDField(read_only=True)
    schedule_id = UUIDField(read_only=True, source='scheduleId')
    creation_date = TimestampField(read_only=True, source='creationDate')
    currency = CharField(read_only=True)
    scenario = CharField(read_only=True),
    status = CharField(read_only=True),
    update_date = TimestampField(read_only=True, source='updateDate'),
    userId = UUIDField(read_only=True)
    data = JSONField(read_only=True)
    transactions = ExternalResourceRelatedField(
        many=True,
        required=False,
        read_only=True,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
    )

    payment_account = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='payment-related',
        self_link_view_name='payment-relationships',
        source='account'
    )

    origin = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='payment-relationships'
    )

    recipient = ExternalResourceRelatedField(
        required=False,
        related_link_view_name='transaction-related',
        self_link_view_name='payment-relationships'
    )

    class Meta(ResourceMeta):
        resource_name = 'payments'


class ForcePaymentSerializer(ResourceSerializer):
    user_id = UUIDField(source='userId', primitive_value=True, required=True)
    original_payment_id = UUIDField(source='originalPaymentId', primitive_value=True, required=True)
    new_payment_id = UUIDField(source='newPaymentId', primitive_value=True, required=False)
    new_payment_status = CharField(read_only=True, required=False),

    class Meta(ResourceMeta):
        resource_name = 'forced_payments'
