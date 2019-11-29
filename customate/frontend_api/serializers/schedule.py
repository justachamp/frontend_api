import logging
import arrow
from traceback import format_exc
from collections import OrderedDict

from customate.settings import PAYMENT_SYSTEM_CLOSING_TIME

from rest_framework.serializers import ValidationError
from rest_framework_json_api.serializers import HyperlinkedModelSerializer
from django.utils.functional import cached_property
from rest_framework.fields import DateField, IntegerField, BooleanField

from core.fields import Currency, SerializerField, FundingSourceType, PayeeType
from frontend_api.fields import ScheduleStatus, SchedulePeriod, SchedulePurpose
from frontend_api.models import FundingSourceDetails
from frontend_api.models import Schedule, Document
from frontend_api.serializers.document import DocumentSerializer
from frontend_api.core.client import PaymentApiClient

from frontend_api.serializers import (
    UUIDField,
    EnumField,
    CharField,
)

logger = logging.getLogger(__name__)


class BaseScheduleSerializer(HyperlinkedModelSerializer):
    @cached_property
    def payment_client(self):
        return PaymentApiClient(self.context.get('request').user)

    def initialize_and_validate_payee_related_fields(self, data):
        """
        We will try to receive some additional information (iban, title etc.) about payee from Payment API,
        and initialize appropriate fields in schedule's data
        :param data: dict of incoming fields from HTTP request
        """
        if data.get('payee_id'):
            pd = self.payment_client.get_payee_details(data.get('payee_id'))
            if pd:
                current_user = self.context.get('request').user
                if data["purpose"] == SchedulePurpose.pay \
                        and pd.type == PayeeType.WALLET.value \
                        and pd.payment_account_id == str(current_user.account.payment_account_id):
                    raise ValidationError({
                        "payee_id": "Current user's payee cannot be used for creation 'pay funds' schedule"
                    })

                data.update({
                    'payee_recipient_name': pd.recipient_name,
                    'payee_recipient_email': pd.recipient_email,
                    'payee_iban': pd.iban,
                    'payee_title': pd.title,
                    'payee_type': pd.type
                })

    def initialize_and_validate_funding_source_related_fields(self, data):
        """
        We will try to receive funding source's types from Payment API, and initialize appropriate fields in
        schedule's data
        :param data: dict of incoming fields from HTTP request
        """
        if data.get('funding_source_id'):
            fs_details = self.payment_client.get_funding_source_details(data.get('funding_source_id'))
            self._check_specific_funding_source(data, fs_details, 'funding_source_id')

            data.update({
                'funding_source_type': self._get_and_validate_funding_source_type(fs_details)
            })

        if 'backup_funding_source_id' in data:
            backup_funding_source_type = None
            if data.get('backup_funding_source_id'):
                fs_details = self.payment_client.get_funding_source_details(data.get('backup_funding_source_id'))
                self._check_specific_funding_source(data, fs_details, 'backup_funding_source_id')
                backup_funding_source_type = self._get_and_validate_backup_funding_source_type(fs_details)

            data.update({
                'backup_funding_source_type': backup_funding_source_type
            })

    def _get_and_validate_funding_source_type(self, fs_details: FundingSourceDetails):
        if fs_details and fs_details.type is not None:
            return fs_details.type
        else:
            raise ValidationError({
                "funding_source_type": "This field is required"
            })

    def _get_and_validate_backup_funding_source_type(self, fs_details: FundingSourceDetails):
        # NOTE: force backup funding source to be of 'WALLET' type only,
        # otherwise we can't process DD/CC payments in a timely manner: they require 7 day gap to be made in advance
        if not fs_details:
            raise ValidationError({
                "backup_funding_source_type": "This field is required"
            })
        elif fs_details.type != FundingSourceType.WALLET.value:
            raise ValidationError({
                "backup_funding_source_id": "Backup funding source is not of type %s" % FundingSourceType.WALLET
            })
        else:
            return fs_details.type

    def _check_specific_funding_source(self, res: OrderedDict, fs_details: FundingSourceDetails, field_name: str):
        """
        :param res: dict of incoming fields from HTTP request
        :param fs_details: funding source details, received from Payment API
        :param field_name: (funding_source_id, backup_funding_source_id)
        """
        user = self.context.get('request').user

        if fs_details.payment_account_id != str(user.account.payment_account_id):
            raise ValidationError({
                field_name: "Invalid funding source payment account"
            })

        # @NOTE: we allow payments from credit card that have different currency
        if fs_details.type != FundingSourceType.CREDIT_CARD.value \
                and fs_details.currency != res.get("currency", self.instance.currency.value if self.instance else None):
            raise ValidationError({
                field_name: "Funding source currency should be the same as schedule currency"
            })

    def assign_uploaded_documents_to_schedule(self, documents):
        logger.info("Assigning uploaded documents to schedule (id=%r)" % self.instance.id,
                    extra={'schedule_id': self.instance.id})
        Document.objects.filter(key__in=[item["key"] for item in documents]).update(schedule=self.instance)


class ScheduleSerializer(BaseScheduleSerializer):
    name = CharField(required=True)
    status = EnumField(enum=ScheduleStatus, default=ScheduleStatus.open, required=False)
    purpose = EnumField(enum=SchedulePurpose, required=True)
    currency = EnumField(enum=Currency, required=True)
    period = EnumField(enum=SchedulePeriod, required=True)
    number_of_payments = IntegerField(required=True)
    number_of_payments_left = IntegerField(required=False, read_only=True)
    number_of_payments_made = IntegerField(required=False, read_only=True)
    start_date = DateField(required=True)
    payment_amount = IntegerField(required=True)
    payment_fee_amount = IntegerField(default=0, required=False)
    deposit_amount = IntegerField(required=False)
    deposit_fee_amount = IntegerField(default=0, required=False)
    deposit_payment_date = DateField(required=False)
    additional_information = CharField(required=False, max_length=140)
    payee_id = UUIDField(required=True)
    payee_title = CharField(required=False)
    payee_recipient_name = CharField(required=False)
    payee_recipient_email = CharField(required=False)
    payee_iban = CharField(required=False)
    payee_type = EnumField(enum=PayeeType, required=False)
    funding_source_id = UUIDField(required=False)
    funding_source_type = EnumField(enum=FundingSourceType, required=False)
    backup_funding_source_id = UUIDField(required=False)
    backup_funding_source_type = EnumField(enum=FundingSourceType, required=False)
    total_paid_sum = IntegerField(default=0, required=False, read_only=True)
    total_sum_to_pay = IntegerField(default=0, required=False, read_only=True)
    total_fee_amount = IntegerField(default=0, required=False, read_only=True)
    origin_user_id = UUIDField(required=False)
    origin_payment_account_id = UUIDField(required=False, read_only=True)
    recipient_user_id = UUIDField(required=False)
    is_overdue = BooleanField(required=False, read_only=True)
    is_processing = BooleanField(required=False, read_only=True)

    documents = SerializerField(resource=DocumentSerializer, many=True, required=False)

    class Meta:
        model = Schedule
        fields = (
            'name', 'status', 'purpose', 'currency', 'period', 'number_of_payments',
            'start_date', 'payment_amount', 'payment_fee_amount', 'deposit_amount', 'deposit_fee_amount',
            'deposit_payment_date', 'additional_information', 'payee_id', 'funding_source_id',
            'backup_funding_source_id', 'payee_title', 'payee_iban', 'payee_recipient_name', 'payee_recipient_email',
            'payee_type', 'documents', 'origin_user_id', 'recipient_user_id',
            'funding_source_type', 'backup_funding_source_type', 'is_overdue', 'is_processing',
            # we can use model properties as well
            'next_payment_date', 'payment_type',
            'number_of_payments_left', 'number_of_payments_made',
            'total_paid_sum', 'total_sum_to_pay', 'total_fee_amount',
            'origin_payment_account_id'
        )

    def validate_name(self, value):
        """
        Make sure we avoid duplicate names for the same user.
        :param name:
        :return:
        """
        request = self.context.get('request')
        logger.info("Validate_name: %r, user=%r" % (value, request.user))

        target_account_ids = request.user.get_all_related_account_ids()
        queryset = Schedule.objects.filter(name=value, origin_user__account__id__in=target_account_ids) \
                   | Schedule.objects.filter(name=value, recipient_user__account__id__in=target_account_ids)

        entries_count = queryset.count()
        if entries_count >= 1:
            # NOTE: no need to provide {"fieldname": "error message"} inside magic validate_{fieldname} methods!
            raise ValidationError("Schedule with such name already exists")
        return value

    def _check_payment_date(self, payment_date, funding_source_type, payee_type):
        """
        Make sure payment date not in the past.
        If payments starts today make sure that we are able to process payment today.
        :param payment_date:
        :return:
        """
        utcnow = arrow.utcnow()
        current_day_start, current_day_end = utcnow.span('day')
        payment_time = arrow.get(payment_date).replace(hour=utcnow.hour, minute=utcnow.minute, second=utcnow.second)
        if payment_time < current_day_start:
            raise ValidationError("Payment date cannot be in the past")
        else:
            # Payment API's closing time restriction can be ignored if we send money between wallets
            if funding_source_type != FundingSourceType.WALLET or payee_type != PayeeType.WALLET:
                ps_hour, ps_minute = PAYMENT_SYSTEM_CLOSING_TIME.split(':')
                ps_closing_time = utcnow.replace(hour=int(ps_hour), minute=int(ps_minute))
                if ps_closing_time < payment_time < current_day_end:
                    raise ValidationError(
                        "You cannot set today's date if the schedule is being created after %s UTC."
                        "Please, try choosing a date in the future." % ps_closing_time.strftime('%H:%M')
                    )

        return payment_date

    def to_internal_value(self, data):
        # This is one of two places where we can perform some kind of pre-initialisation for data (before it will be
        # sent to validation)
        self.initialize_and_validate_payee_related_fields(data)
        self.initialize_and_validate_funding_source_related_fields(data)

        return super().to_internal_value(data)

    # validate_{fieldname} also works
    def validate(self, res: OrderedDict):
        """
        Apply custom validation on whole resource.
        See more at: https://www.django-rest-framework.org/api-guide/serializers/#validation
        :param res: Incoming data
        :type res: OrderedDict
        :return: validated res
        :rtype: OrderedDict
        """
        logger.info(f"Validating data for schedule's creation", extra={'scheduleDict': res})

        try:
            if res.get('start_date'):
                self._check_payment_date(res["start_date"], res.get('funding_source_type'), res.get('payee_type'))

            if res.get("deposit_payment_date"):
                if res["deposit_payment_date"] > res["start_date"]:
                    raise ValidationError({
                        "deposit_payment_date": "Deposit payment date must come prior to start date"
                    })

                self._check_payment_date(res["deposit_payment_date"], res.get('funding_source_type'),
                                         res.get('payee_type'))

                deposit_amount = res.get("deposit_amount")
                if deposit_amount is None:
                    raise ValidationError({"deposit_amount": "Please, specify deposit amount"})

                if int(deposit_amount) < 0:
                    raise ValidationError({"deposit_amount": "Deposit amount should be positive number"})

            if int(res["payment_amount"]) < 0:
                raise ValidationError({"payment_amount": "Payment amount should be positive number"})

            if int(res["payment_fee_amount"]) < 0:
                raise ValidationError({"payment_fee_amount": "Payment fee amount should be positive number"})

            if res.get("deposit_fee_amount") and int(res["deposit_fee_amount"]) < 0:
                raise ValidationError({"deposit_fee_amount": "Deposit fee amount should be positive number"})

            if res.get("purpose") == SchedulePurpose.pay:
                # Verify first funding source
                if res.get("funding_source_id") is None:
                    raise ValidationError({"funding_source_id": "This field is required."})

                # Verify backup funding source
                if res.get("backup_funding_source_id") and res["backup_funding_source_id"] == res["funding_source_id"]:
                    raise ValidationError({
                        "backup_funding_source_id": "Backup funding source can not be the same as default"
                    })

        except (ValueError, TypeError):
            logger.error("Validation failed due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")

        return res


class UpdateScheduleSerializer(BaseScheduleSerializer):
    name = CharField(required=True)
    number_of_payments = IntegerField(required=True)
    payment_amount = IntegerField(required=True)
    payment_fee_amount = IntegerField(default=0, required=False)
    deposit_amount = IntegerField(required=False)
    deposit_fee_amount = IntegerField(default=0, required=False)
    additional_information = CharField(required=False, allow_blank=True, allow_null=True, max_length=140)
    funding_source_id = UUIDField(required=True)
    funding_source_type = EnumField(enum=FundingSourceType, required=False)
    backup_funding_source_id = UUIDField(required=False, allow_null=True)
    backup_funding_source_type = EnumField(enum=FundingSourceType, required=False, allow_null=True)
    documents = SerializerField(resource=DocumentSerializer, many=True, required=False)

    class Meta:
        model = Schedule
        fields = (
            'name', 'number_of_payments', 'payment_amount', 'payment_fee_amount', 'deposit_amount',
            'deposit_fee_amount', 'additional_information', 'funding_source_id', 'backup_funding_source_id',
            'documents', 'funding_source_type', 'backup_funding_source_type'
        )

    def validate_name(self, value):
        """
        Make sure we avoid duplicate names for the same user.
        :param name:
        :return:
        """
        request = self.context.get('request')
        logger.info("Validate_name: %r, user=%r" % (value, request.user))

        # Searching for duplicate by name (but excluding current schedule from selection)
        target_account_ids = request.user.get_all_related_account_ids()
        queryset = Schedule.objects.filter(name=value, origin_user__account__id__in=target_account_ids).exclude(
            id=self.instance.id) \
                   | Schedule.objects.filter(name=value, recipient_user__account__id__in=target_account_ids).exclude(
            id=self.instance.id)

        entries_count = queryset.count()
        if entries_count >= 1:
            raise ValidationError("Schedule with such name already exists")
        return value

    def to_internal_value(self, data):
        # This is one of two places where we can perform some kind of pre-initialisation for data (before it will be
        # sent to validation)
        self.initialize_and_validate_payee_related_fields(data)
        self.initialize_and_validate_funding_source_related_fields(data)

        return super().to_internal_value(data)

    def validate(self, res: OrderedDict):
        """
        Apply custom validation on whole resource.
        See more at: https://www.django-rest-framework.org/api-guide/serializers/#validation
        :param res: Incoming data
        :type res: OrderedDict
        :return: validated res
        :rtype: OrderedDict
        """
        logger.info(f"Validating data for schedule's update (id={res.get('id')})", extra={'scheduleDict': res})

        try:
            if int(res["payment_amount"]) < 0:
                raise ValidationError({"payment_amount": "Payment amount should be positive number"})

            if int(res["payment_fee_amount"]) < 0:
                raise ValidationError({"payment_fee_amount": "Payment fee amount should be positive number"})

            if res.get("deposit_amount"):
                if int(res["deposit_amount"]) < 0:
                    raise ValidationError({"deposit_fee_amount": "Deposit amount should be positive number"})

                if int(res["deposit_amount"]) != self.instance.deposit_amount:
                    raise ValidationError({"deposit_amount": "Deposit amount cannot be updated"})

            if res.get("deposit_fee_amount") and int(res["deposit_fee_amount"]) < 0:
                raise ValidationError({"deposit_fee_amount": "Deposit fee amount should be positive number"})

            if res.get("backup_funding_source_id") and res["backup_funding_source_id"] == res["funding_source_id"]:
                raise ValidationError({
                    "backup_funding_source_id": "Backup funding source can not be the same as default"
                })

            if self.instance.purpose == SchedulePurpose.receive and int(
                    res["payment_amount"]) != self.instance.payment_amount:
                raise ValidationError({"payment_amount": "Payment amount cannot be updated"})

        except (ValueError, TypeError):
            logger.error("Validation failed during update operation, due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")

        return res


class ScheduleAcceptanceSerializer(BaseScheduleSerializer):
    funding_source_id = UUIDField(required=True)
    funding_source_type = EnumField(enum=FundingSourceType, required=False)
    backup_funding_source_id = UUIDField(required=False)
    backup_funding_source_type = EnumField(enum=FundingSourceType, required=False)
    payment_fee_amount = IntegerField(default=0, required=False)
    deposit_fee_amount = IntegerField(default=0, required=False)

    class Meta:
        model = Schedule
        fields = (
            'funding_source_id', 'funding_source_type', 'backup_funding_source_id', 'backup_funding_source_type',
            'payment_fee_amount', 'deposit_fee_amount'
        )

    def to_internal_value(self, data):
        # This is one of two places where we can perform some kind of pre-initialisation for data (before it will be
        # sent to validation)
        self.initialize_and_validate_payee_related_fields(data)
        self.initialize_and_validate_funding_source_related_fields(data)

        return super().to_internal_value(data)

    def validate(self, res: OrderedDict):
        """
        Apply custom validation on whole resource.
        See more at: https://www.django-rest-framework.org/api-guide/serializers/#validation
        :param res: Incoming data
        :type res: OrderedDict
        :return: validated res
        :rtype: OrderedDict
        """
        logger.info("Validating data for schedule's update (data=%r)" % res)

        try:
            if res.get("payment_fee_amount") and int(res["payment_fee_amount"]) < 0:
                raise ValidationError({"payment_fee_amount": "Payment fee amount should be positive number"})

            if res.get("deposit_fee_amount") and int(res["deposit_fee_amount"]) < 0:
                raise ValidationError({"deposit_fee_amount": "Deposit fee amount should be positive number"})

        except (ValueError, TypeError):
            logger.error("Validation failed due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")
        return res
