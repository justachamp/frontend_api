from collections import OrderedDict
import logging
from traceback import format_exc
from rest_framework.serializers import ValidationError

from rest_framework_json_api.serializers import (
    HyperlinkedModelSerializer,
    IntegerField)

from core.fields import Currency, TimestampField
from frontend_api.fields import ScheduleStatus, SchedulePeriod, SchedulePurpose
from frontend_api.models import Schedule

from ..serializers import (
    UUIDField,
    EnumField,
    CharField,
    UniqueValidator,
)

logger = logging.getLogger(__name__)


class ScheduleSerializer(HyperlinkedModelSerializer):
    name = CharField(required=True, validators=[UniqueValidator(queryset=Schedule.objects.all())])
    status = EnumField(enum=ScheduleStatus, default=ScheduleStatus.open, required=False)
    purpose = EnumField(enum=SchedulePurpose, required=True)
    currency = EnumField(enum=Currency, required=True)
    period = EnumField(enum=SchedulePeriod, required=True)
    number_of_payments_left = IntegerField(required=True)
    start_date = TimestampField
    payment_amount = IntegerField(required=True)
    deposit_amount = IntegerField(required=False)
    deposit_payment_date = TimestampField(required=False)  # TODO: Validate that this should be strictly < start_date
    additional_information = CharField(required=False)
    payee_id = UUIDField(required=True)
    funding_source_id = UUIDField(required=True)
    total_paid_sum = IntegerField(default=0)
    total_sum_to_pay = IntegerField(default=0)

    class Meta:
        model = Schedule
        fields = (
            'name', 'status', 'purpose', 'currency', 'period', 'number_of_payments_left',
            'start_date', 'payment_amount', 'deposit_amount', 'deposit_payment_date',
            'additional_information', 'payee_id', 'funding_source_id',
            'total_paid_sum', 'total_sum_to_pay'
        )

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
            # TODO: custom validation logic here
            # if res["deposit_payment_date"] > res["start_date"]:
            #     raise ValidationError("Deposit payment date must come prior to start date")
            pass
        except Exception as e:
            logger.error(": %r" % format_exc())
            raise ValidationError("Schedule validation failed")

        return res

