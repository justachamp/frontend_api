import logging
import arrow
from traceback import format_exc
from collections import OrderedDict

from customate.settings import PAYMENT_SYSTEM_CLOSING_TIME

from rest_framework.serializers import ValidationError
from rest_framework_json_api.serializers import HyperlinkedModelSerializer
from rest_framework.fields import DateField, IntegerField

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


class ScheduleSerializer(HyperlinkedModelSerializer):
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
    fee_amount = IntegerField(default=0, required=False)
    deposit_amount = IntegerField(required=False)
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
    origin_user_id = UUIDField(required=False)
    recipient_user_id = UUIDField(required=False)

    documents = SerializerField(resource=DocumentSerializer, many=True, required=False)

    class Meta:
        model = Schedule
        fields = (
            'name', 'status', 'purpose', 'currency', 'period', 'number_of_payments',
            'start_date', 'payment_amount', 'fee_amount', 'deposit_amount', 'deposit_payment_date',
            'additional_information', 'payee_id', 'funding_source_id', 'backup_funding_source_id', 'payee_title',
            'payee_iban', 'payee_recipient_name', 'payee_recipient_email',
            'payee_type', 'documents', 'origin_user_id', 'recipient_user_id',
            'funding_source_type', 'backup_funding_source_type',
            # we can use model properties as well
            'next_payment_date', 'payment_type',
            'number_of_payments_left', 'number_of_payments_made',
            'total_paid_sum', 'total_sum_to_pay'
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

    def validate_start_date(self, value):
        return self.check_payment_date(value)

    def validate_deposit_payment_date(self, value):
        return self.check_payment_date(value)

    def check_payment_date(self, payment_date):
        """
        Make sure payment date not in the past.
        If payments starts today make sure that we are able to process payment today.
        :param payment_date:
        :return:
        """
        utcnow = arrow.utcnow()
        current_day_start, current_day_end = utcnow.span('day')
        ps_hour, ps_minute = PAYMENT_SYSTEM_CLOSING_TIME.split(':')
        ps_closing_time = utcnow.replace(hour=int(ps_hour), minute=int(ps_minute))
        payment_time = arrow.get(payment_date).replace(hour=utcnow.hour, minute=utcnow.minute, second=utcnow.second)
        if payment_time < current_day_start:
            raise ValidationError("Payment date cannot be in the past")
        elif ps_closing_time < payment_time < current_day_end:
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
        payment_client = PaymentApiClient(user)

        fs = payment_client.get_funding_source_details(res[field_name])
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
            if res.get("deposit_payment_date"):
                if res["deposit_payment_date"] > res["start_date"]:
                    raise ValidationError({
                        "deposit_payment_date": "Deposit payment date must come prior to start date"
                    })

                deposit_amount = res.get("deposit_amount")
                if deposit_amount is None:
                    raise ValidationError({"deposit_amount": "Please, specify deposit amount"})

                if int(deposit_amount) < 0:
                    raise ValidationError({"deposit_amount": "Deposit amount should be positive number"})

            if int(res["payment_amount"]) < 0:
                raise ValidationError({"payment_amount": "Payment amount should be positive number"})

            if int(res["fee_amount"]) < 0:
                raise ValidationError({"fee_amount": "Fee amount should be positive number"})

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


class ScheduleAcceptanceSerializer(HyperlinkedModelSerializer):
    funding_source_id = UUIDField(required=True)
    backup_funding_source_id = UUIDField(required=False)
    fee_amount = IntegerField(default=0, required=False)

    class Meta:
        model = Schedule
        fields = (
            'funding_source_id', 'backup_funding_source_id', 'fee_amount'
        )

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
            if res.get("fee_amount") and int(res["fee_amount"]) < 0:
                raise ValidationError({"fee_amount": "Fee amount should be positive number"})

        except (ValueError, TypeError):
            logger.error("Validation failed due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")
        return res
