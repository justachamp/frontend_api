import logging
from typing import Dict
from collections import OrderedDict
from uuid import UUID
from rest_framework.serializers import ValidationError
from rest_framework.fields import DateField, IntegerField, BooleanField
from rest_framework_json_api.serializers import HyperlinkedModelSerializer, SerializerMethodField

from frontend_api.models.escrow import Escrow, EscrowStatus, EscrowOperationType, EscrowOperation, \
    EscrowOperationStatus, EscrowPurpose
from core.fields import Currency, SerializerField, PayeeType, FundingSourceType

import external_apis.payment.service as payment_service
from frontend_api.models.escrow import Escrow, EscrowStatus
from frontend_api.serializers.document import DocumentSerializer
from frontend_api.serializers import (
    UUIDField,
    EnumField,
    CharField,
)

logger = logging.getLogger(__name__)


class BaseEscrowSerializer(HyperlinkedModelSerializer):

    def validate_payee_related_fields(self, payee_id: str) -> Dict:
        """
        We will try to receive some additional information (iban, title etc.) about payee from Payment API,
        and initialize appropriate fields in escrow's data
        :param payee_id:
        """
        response = {}
        if not payee_id:
            return response

        try:
            pd = payment_service.Payee.get(payee_id=UUID(payee_id))
        except Exception:
            logger.error("Got empty 'payee_id' or 'payee_details'. Payee_id: %s.", payee_id)
            raise ValidationError("Payment service is not available. Try again later.")

        response.update({
            'payee_recipient_name': pd.recipient_name,
            'payee_recipient_email': pd.recipient_email,
            'payee_iban': pd.iban
        })

        return response

    def is_valid(self, *args, **kwargs):
        return super().is_valid(raise_exception=True)

    def run_validation(self, *args, **kwargs):
        data = super().run_validation(*args, **kwargs)
        payee_details = self.validate_payee_related_fields(payee_id=data.get("payee_id"))
        data.update(payee_details)

        return data

    def assign_uploaded_documents_to_escrow(self, documents):
        """
        TODO:
        :param documents:
        :return:
        """
        logger.info("Assigning uploaded documents to schedule (id=%r)" % self.instance.id, extra={
            'schedule_id': self.instance.id
        })
        raise NotImplemented()
        # Document.objects.filter(key__in=[item["key"] for item in documents]).update(schedule=self.instance)


class EscrowSerializer(BaseEscrowSerializer):
    name = CharField(required=True)
    status = EnumField(enum=EscrowStatus, default=EscrowStatus.pending, required=False)

    # Funder
    funder_user_id = UUIDField(required=True)

    # Recipient
    recipient_user_id = UUIDField(required=True)

    currency = EnumField(enum=Currency, required=True)

    # initial payment amount
    initial_amount = IntegerField(required=True)
    can_close = BooleanField(required=False, read_only=True)
    can_release_funds = BooleanField(required=False, read_only=True)

    # Payment API details
    wallet_id = UUIDField(required=False)

    # Payee
    payee_id = UUIDField(required=True)
    payee_recipient_name = CharField(required=False)
    payee_recipient_email = CharField(required=False)
    payee_iban = CharField(required=False)

    # Transit Payee
    transit_payee_id = UUIDField(required=False)

    # Transit FS
    transit_funding_source_id = UUIDField(required=False)

    additional_information = CharField(required=False, max_length=140)
    documents = SerializerField(resource=DocumentSerializer, many=True, required=False)

    funding_deadline = DateField(required=False)

    purpose = SerializerMethodField()
    counterpart_email = SerializerMethodField()
    counterpart_name = SerializerMethodField()
    has_pending_operations = SerializerMethodField()

    class Meta:
        model = Escrow
        fields = (
            'name', 'status',
            'funder_user_id',
            'recipient_user_id',
            'currency',
            'wallet_id',
            'payee_id', 'payee_iban', 'payee_recipient_name', 'payee_recipient_email',

            'transit_payee_id',
            'transit_funding_source_id',

            'additional_information',
            'documents',
            'counterpart_email',
            'counterpart_name',
            'purpose',

            # we can use model properties as well
            'funder_payment_account_id',
            'funding_deadline',
            'balance',
            'initial_amount',
            'closing_date',
            'can_close',
            'can_release_funds',
            'has_pending_operations'
        )

    def _get_counterpart(self, escrow: Escrow):
        """
        Define correct counterpart based on user that performed the request

        :param escrow: Escrow
        :return counterpart: User
        """
        current_user = self.context.get('request').user
        result = escrow.funder_user

        if current_user.id == escrow.funder_user.id:
            result = escrow.recipient_user

        return result

    def get_counterpart_email(self, escrow) -> str:
        """
        :param escrow: Escrow
        :return counterpart's email: str
        """
        return self._get_counterpart(escrow).email

    def get_counterpart_name(self, escrow) -> str:
        """
        :param escrow: Escrow
        :return counterpart's name: str
        """
        counterpart = self._get_counterpart(escrow)
        return '%s %s' % (counterpart.first_name, counterpart.last_name)

    def get_purpose(self, escrow) -> str:
        """

        :param escrow: Escrow
        :return Escrow's purpose: str
        """
        current_user = self.context.get('request').user
        result = EscrowPurpose.receive.value

        if current_user.id == escrow.funder_user.id:
            result = EscrowPurpose.pay.value

        return result

    def get_has_pending_operations(self, escrow) -> bool:
        current_user = self.context.get('request').user
        return escrow.has_pending_operations_for_user(current_user)

    def validate_name(self, value):
        """
        Make sure we avoid duplicate names for the same user.
        :param name:
        :return:
        """
        request = self.context.get('request')
        logger.info("Validate_name: %r, user=%r" % (value, request.user))

        target_account_ids = request.user.get_all_related_account_ids()
        queryset = Escrow.objects.filter(name=value, funder_user__account__id__in=target_account_ids) \
                   | Escrow.objects.filter(name=value, recipient_user__account__id__in=target_account_ids)

        entries_count = queryset.count()
        if entries_count >= 1:
            # NOTE: no need to provide {"fieldname": "error message"} inside magic validate_{fieldname} methods!
            raise ValidationError("Escrow with such name already exists")
        return value

    def validate_payee_id(self, value):
        """

        :param value:
        :return:
        """
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
        logger.info(f"Validating data for schedule's creation", extra={'scheduleDict': res})
        # try:
        #     if res.get('start_date'):
        #         self._check_payment_date(res["start_date"], res.get('funding_source_type'), res.get('payee_type'))
        #
        #     if res.get("deposit_payment_date"):
        #         if res["deposit_payment_date"] > res["start_date"]:
        #             raise ValidationError({
        #                 "deposit_payment_date": "Deposit payment date must come prior to start date"
        #             })
        #
        #         self._check_payment_date(res["deposit_payment_date"], res.get('funding_source_type'),
        #                                  res.get('payee_type'))
        #
        #         deposit_amount = res.get("deposit_amount")
        #         if deposit_amount is None:
        #             raise ValidationError({"deposit_amount": "Please, specify deposit amount"})
        #
        #         if int(deposit_amount) < 0:
        #             raise ValidationError({"deposit_amount": "Deposit amount should be positive number"})
        #
        #     if int(res["payment_amount"]) < 0:
        #         raise ValidationError({"payment_amount": "Payment amount should be positive number"})
        #
        #     if int(res["payment_fee_amount"]) < 0:
        #         raise ValidationError({"payment_fee_amount": "Payment fee amount should be positive number"})
        #
        #     if res.get("deposit_fee_amount") and int(res["deposit_fee_amount"]) < 0:
        #         raise ValidationError({"deposit_fee_amount": "Deposit fee amount should be positive number"})
        #
        #
        # except (ValueError, TypeError):
        #     logger.error("Validation failed due to: %r" % format_exc())
        #     raise ValidationError("Schedule validation failed")

        return res


class EscrowOperationSerializer(HyperlinkedModelSerializer):
    type = EnumField(enum=EscrowOperationType, required=True)
    status = EnumField(enum=EscrowOperationStatus, default=EscrowOperationStatus.pending, required=False,
                       read_only=True)
    escrow_id = UUIDField(required=True)
    additional_information = CharField(required=False)
    is_action_required = SerializerMethodField()

    class Meta:
        model = EscrowOperation
        fields = (
            'created_at',
            'type',
            'escrow_id',
            'additional_information',
            'status',
            'is_action_required'
        )

    # We need to require actions only from operation's counterpart user
    def get_is_action_required(self, escrow_operation) -> bool:
        """
        Whether this EscrowOperation requires some action from current user

        :param escrow_operation: EscrowOperation
        :return:
        """
        current_user = self.context.get('request').user
        return not escrow_operation.creator.id == current_user.id
