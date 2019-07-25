import logging
import arrow
from traceback import format_exc
from collections import OrderedDict

#from rest_framework.exceptions import ValidationError
from rest_framework.serializers import ValidationError
from rest_framework_json_api.serializers import HyperlinkedModelSerializer
from rest_framework.fields import DateField, IntegerField

from core.fields import Currency
from frontend_api.fields import ScheduleStatus, SchedulePeriod, SchedulePurpose
from frontend_api.models.schedule import Schedule

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
    number_of_payments_left = IntegerField(required=True)
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
    funding_source_id = UUIDField(required=True)
    total_paid_sum = IntegerField(default=0, required=False)
    total_sum_to_pay = IntegerField(default=0, required=False)

    class Meta:
        model = Schedule
        fields = (
            'name', 'status', 'purpose', 'currency', 'period', 'number_of_payments_left',
            'start_date', 'payment_amount', 'fee_amount', 'deposit_amount', 'deposit_payment_date',
            'additional_information', 'payee_id', 'funding_source_id', 'payee_title',
            'total_paid_sum', 'total_sum_to_pay', 'payee_iban', 'payee_recipient_name', 'payee_recipient_email'
        )

    def validate_name(self, value):
        """

        :param name:
        :return:
        """
        request = self.context.get('request')
        logger.info("Validate_name: %r, user=%r" % (value, request.user))
        entries_count = Schedule.objects.filter(name=value, user=request.user).count()
        if entries_count >= 1:
            raise ValidationError(["Schedule with such name already exists"])

        # raise ValidationError({
        #     api_settings.NON_FIELD_ERRORS_KEY: [message]
        # }, code='invalid')

        return value

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
                raise ValidationError({"payment_amount": "Fee amount should be positive number"})

            if arrow.get("%sT23:59:59" % res["start_date"]) < arrow.utcnow():
                raise ValidationError({"start_date": "Start date cannot be in the past"})

        except (ValueError, TypeError):
            logger.error("Validation failed due to: %r" % format_exc())
            raise ValidationError("Schedule validation failed")

        return res
