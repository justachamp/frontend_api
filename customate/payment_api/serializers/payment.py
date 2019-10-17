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
from frontend_api import tasks
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

    def notify_users_about_status(self, status: str, sender_id: str, recipient_email: str, amount: int):
        funds_recipient = get_user_model().objects.get(email=recipient_email)
        funds_sender = get_user_model().objects.get(id=sender_id)

        funds_recipients_emails = helpers.get_funds_recipients_emails(funds_recipient=funds_recipient)
        funds_senders_emails = helpers.get_funds_senders_emails(funds_sender=funds_sender)
        funds_recipients_phones = helpers.get_funds_recipients_phones(funds_recipient=funds_recipient)
        funds_senders_phones = helpers.get_funds_senders_phones(funds_sender=funds_sender)

        # Handle "FAILED transaction" case
        if status == PaymentStatusType.FAILED.value:
            for email in funds_senders_emails:
                context = {'original_amount': amount / 100}
                message = signals.get_ses_email_payload(tpl_filename='notifications/email_transaction_failed.html',
                                                        tpl_context=context)
                tasks.send_notification_email.delay(to_address=email, message=message)
            for phone_number in funds_senders_phones:
                message = "Transaction failed."
                tasks.send_notification_sms.delay(to_phone_number=phone_number, message=message)

        # Handle "SUCCESS transaction" case
        if status == PaymentStatusType.SUCCESS.value:
            # Notify funds senders
            # Because sender and recipient might be the same user, remove him from senders notifications
            for email in [item for item in funds_senders_emails if item not in funds_recipients_emails]:
                context = {'original_amount': amount / 100}
                message = helpers.get_ses_email_payload(tpl_filename='notifications/email_senders_balance_updated.html',
                                                        tpl_context=context)
                tasks.send_notification_email.delay(to_address=email, message=message)
            for phone_number in [item for item in funds_senders_phones if item not in funds_recipients_phones]:
                message = 'Your balance has changed.'
                tasks.send_notification_sms.delay(to_phone_number=phone_number, message=message)
            # Notify funds recipients
            for email in funds_recipients_emails:
                context = {'original_amount': amount / 100}
                message = helpers.get_ses_email_payload(tpl_filename='notifications/email_recipients_balance_updated.html',
                                                        tpl_context=context)
                tasks.send_notification_email.delay(to_address=email, message=message)
            for phone_number in funds_recipients_phones:
                message = 'Your balance has changed.'
                tasks.send_notification_sms.delay(to_phone_number=phone_number, message=message)


    def create(self, validated_data):
        payment = super().create(validated_data)
        self.notify_users_about_status(status=payment.status, sender_id=payment.userId,
                                       recipient_email=payment.recipient.data["recipient"]["email"],
                                       amount=validated_data["data"]["amount"])
        return payment

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
