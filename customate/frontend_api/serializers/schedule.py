import logging
import arrow
from traceback import format_exc
from collections import OrderedDict

from customate.settings import PAYMENT_SYSTEM_CLOSING_TIME

from rest_framework.serializers import ValidationError
from rest_framework_json_api.serializers import HyperlinkedModelSerializer
from rest_framework.fields import DateField, IntegerField
from django.utils.functional import cached_property

from core.fields import Currency, SerializerField, FundingSourceType, PayeeType
from frontend_api.fields import ScheduleStatus, SchedulePeriod, SchedulePurpose
from frontend_api.models.schedule import Schedule
from frontend_api.models.document import Document
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

    def _initialize_additional_schedule_fields(self, data):
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

        if data.get('funding_source_id'):
            data.update({
                'funding_source_type': self._get_and_validate_funding_source_type(data.get("funding_source_id"))
            })

        if data.get('backup_funding_source_id'):
            data.update({
                'backup_funding_source_type': self._get_and_validate_backup_funding_source_type(data.get("backup_funding_source_id"))
            })

    def _get_and_validate_funding_source_type(self, funding_source_id):
        if funding_source_id:
            fd = self.payment_client.get_funding_source_details(funding_source_id)
            if fd and fd.type is not None:
                return fd.type
            else:
                raise ValidationError({
                    "funding_source_type": "This field is required"
                })

    def _get_and_validate_backup_funding_source_type(self, backup_funding_source_id):
        # NOTE: force backup funding source to be of 'WALLET' type only,
        # otherwise we can't process DD/CC payments in a timely manner: they require 7day gap to be made in advance
        if backup_funding_source_id:
            fd_backup = self.payment_client.get_funding_source_details(backup_funding_source_id)
            # NOTE: we do not support backup_funding_source type other than 'WALLET'
            if not fd_backup:
                raise ValidationError({
                    "backup_funding_source_type": "This field is required"
                })
            elif fd_backup.type != FundingSourceType.WALLET.value:
                raise ValidationError({
                    "backup_funding_source_id": "Backup funding source is not of type %s" % FundingSourceType.WALLET
                })
            else:
                return fd_backup.type


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
    additional_information = CharField(required=False)
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

    documents = SerializerField(resource=DocumentSerializer, many=True, required=False)

    class Meta:
        model = Schedule
        fields = (
            'name', 'status', 'purpose', 'currency', 'period', 'number_of_payments',
            'start_date', 'payment_amount', 'payment_fee_amount', 'deposit_amount', 'deposit_fee_amount',
            'deposit_payment_date', 'additional_information', 'payee_id', 'funding_source_id',
            'backup_funding_source_id', 'payee_title', 'payee_iban', 'payee_recipient_name', 'payee_recipient_email',
            'payee_type', 'documents', 'origin_user_id', 'recipient_user_id',
            'funding_source_type', 'backup_funding_source_type',
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
        if self.instance:
            queryset = Schedule.objects.filter(name=value, origin_user__account__id__in=target_account_ids).exclude(id=self.instance.id) \
                       | Schedule.objects.filter(name=value, recipient_user__account__id__in=target_account_ids).exclude(id=self.instance.id)
        else:
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

    def check_specific_funding_source(self, res: OrderedDict, field_name: str):
        """
        Calls payment-api and verifies that funding sources are correct.
        :param res: dict of incoming fields from HTTP request
        :param field_name: (funding_source_id, backup_funding_source_id)
        :return:
        """
        user = self.context.get('request').user

        fs = self.payment_client.get_funding_source_details(res[field_name])
        if fs.payment_account_id != str(user.account.payment_account_id):
            raise ValidationError({
                field_name: "Invalid funding source payment account"
            })

        # @NOTE: we allow payments from credit card that have different currency
        if fs.type != FundingSourceType.CREDIT_CARD.value and fs.currency != res["currency"].value:
            raise ValidationError({
                field_name: "Funding source currency should be the same as schedule currency"
            })

        return

    def to_internal_value(self, data):
        self._initialize_additional_schedule_fields(data)
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
        logger.info("VALIDATE, res=%r" % res)

        try:
            if res.get('start_date'):
                self._check_payment_date(res["start_date"], res.get('funding_source_type'), res.get('payee_type'))

            if res.get("deposit_payment_date"):
                if res["deposit_payment_date"] > res["start_date"]:
                    raise ValidationError({
                        "deposit_payment_date": "Deposit payment date must come prior to start date"
                    })

                self._check_payment_date(res["deposit_payment_date"], res.get('funding_source_type'), res.get('payee_type'))

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
                self.check_specific_funding_source(res, field_name="funding_source_id")

                # Verify backup funding source
                if res.get("backup_funding_source_id"):
                    if res["backup_funding_source_id"] == res["funding_source_id"]:
                        raise ValidationError({
                            "backup_funding_source_id": "Backup funding source can not be the same as default"
                        })
                    self.check_specific_funding_source(res, field_name="backup_funding_source_id")

        except (ValueError, TypeError):
            logger.error("Validation failed due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")

        return res

    def assign_uploaded_documents_to_schedule(self, documents):
        Document.objects.filter(id__in=[item["id"] for item in documents]).update(schedule=self.instance)


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
        self._initialize_additional_schedule_fields(data)
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
        logger.info("VALIDATE, res=%r" % res)

        try:
            if res.get("payment_fee_amount") and int(res["payment_fee_amount"]) < 0:
                raise ValidationError({"payment_fee_amount": "Payment fee amount should be positive number"})

            if res.get("deposit_fee_amount") and int(res["deposit_fee_amount"]) < 0:
                raise ValidationError({"deposit_fee_amount": "Deposit fee amount should be positive number"})

        except (ValueError, TypeError):
            logger.error("Validation failed due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")
        return res
