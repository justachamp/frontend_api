import logging
from collections import OrderedDict

from rest_framework.serializers import ValidationError
from rest_framework.fields import DateField, IntegerField, BooleanField

from rest_framework_json_api.serializers import HyperlinkedModelSerializer

from core.fields import Currency, SerializerField, PayeeType

from frontend_api.models.escrow import Escrow, EscrowStatus
from frontend_api.serializers.document import DocumentSerializer

from frontend_api.serializers import (
    UUIDField,
    EnumField,
    CharField,
)

logger = logging.getLogger(__name__)


class BaseEscrowSerializer(HyperlinkedModelSerializer):
    # @cached_property
    # def payment_client(self):
    #     return PaymentApiClient(self.context.get('request').user)

    # def initialize_and_validate_payee_related_fields(self, data):
    #     """
    #     We will try to receive some additional information (iban, title etc.) about payee from Payment API,
    #     and initialize appropriate fields in schedule's data
    #     :param data: dict of incoming fields from HTTP request
    #     """
    #     if data.get('payee_id'):
    #         pd = self.payment_client.get_payee_details(data.get('payee_id'))
    #         if pd:
    #             current_user = self.context.get('request').user
    #             if data["purpose"] == SchedulePurpose.pay \
    #                     and pd.type == PayeeType.WALLET.value \
    #                     and pd.payment_account_id == str(current_user.account.payment_account_id):
    #                 raise ValidationError({
    #                     "payee_id": "Current user's payee cannot be used for creation 'pay funds' schedule"
    #                 })
    #
    #             data.update({
    #                 'payee_recipient_name': pd.recipient_name,
    #                 'payee_recipient_email': pd.recipient_email,
    #                 'payee_iban': pd.iban,
    #                 'payee_title': pd.title,
    #                 'payee_type': pd.type
    #             })
    #
    # def initialize_and_validate_funding_source_related_fields(self, data):
    #     """
    #     We will try to receive funding source's types from Payment API, and initialize appropriate fields in
    #     schedule's data
    #     :param data: dict of incoming fields from HTTP request
    #     """
    #     if data.get('funding_source_id'):
    #         fs_details = self.payment_client.get_funding_source_details(data.get('funding_source_id'))
    #         self._check_specific_funding_source(data, fs_details, 'funding_source_id')
    #
    #         data.update({
    #             'funding_source_type': self._get_and_validate_funding_source_type(fs_details)
    #         })
    #
    #     if 'backup_funding_source_id' in data:
    #         backup_funding_source_type = None
    #         if data.get('backup_funding_source_id'):
    #             fs_details = self.payment_client.get_funding_source_details(data.get('backup_funding_source_id'))
    #             self._check_specific_funding_source(data, fs_details, 'backup_funding_source_id')
    #             backup_funding_source_type = self._get_and_validate_backup_funding_source_type(fs_details)
    #
    #         data.update({
    #             'backup_funding_source_type': backup_funding_source_type
    #         })

    # def _get_and_validate_funding_source_type(self, fs_details: FundingSourceDetails):
    #     if fs_details and fs_details.type is not None:
    #         return fs_details.type
    #     else:
    #         raise ValidationError({
    #             "funding_source_type": "This field is required"
    #         })
    #
    # def _get_and_validate_backup_funding_source_type(self, fs_details: FundingSourceDetails):
    #     # NOTE: force backup funding source to be of 'WALLET' type only,
    #     # otherwise we can't process DD/CC payments in a timely manner: they require 7 day gap to be made in advance
    #     if not fs_details:
    #         raise ValidationError({
    #             "backup_funding_source_type": "This field is required"
    #         })
    #     elif fs_details.type != FundingSourceType.WALLET.value:
    #         raise ValidationError({
    #             "backup_funding_source_id": "Backup funding source is not of type %s" % FundingSourceType.WALLET
    #         })
    #     else:
    #         return fs_details.type
    #
    # def _check_specific_funding_source(self, res: OrderedDict, fs_details: FundingSourceDetails, field_name: str):
    #     """
    #     :param res: dict of incoming fields from HTTP request
    #     :param fs_details: funding source details, received from Payment API
    #     :param field_name: (funding_source_id, backup_funding_source_id)
    #     """
    #     user = self.context.get('request').user
    #
    #     if fs_details.payment_account_id != str(user.account.payment_account_id):
    #         raise ValidationError({
    #             field_name: "Invalid funding source payment account"
    #         })
    #
    #     # @NOTE: we allow payments from credit card that have different currency
    #     if fs_details.type != FundingSourceType.CREDIT_CARD.value \
    #             and fs_details.currency != res.get("currency", self.instance.currency.value if self.instance else None):
    #         raise ValidationError({
    #             field_name: "Funding source currency should be the same as schedule currency"
    #         })

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

    # Payment API details
    wallet_id = UUIDField(required=False)

    # Payee
    payee_id = UUIDField(required=True)

    payee_title = CharField(required=False)
    payee_recipient_name = CharField(required=False)
    payee_recipient_email = CharField(required=False)
    payee_iban = CharField(required=False)
    payee_type = EnumField(enum=PayeeType, required=False)

    # Transit Payee
    transit_payee_id = UUIDField(required=False)

    # Transit FS
    transit_funding_source_id = UUIDField(required=False)

    additional_information = CharField(required=False, max_length=140)
    documents = SerializerField(resource=DocumentSerializer, many=True, required=False)

    funding_deadline = DateField(required=False)

    class Meta:
        model = Escrow
        fields = (
            'name', 'status',
            'funder_user_id',
            'recipient_user_id',
            'currency',
            'wallet_id',
            'payee_id', 'payee_title', 'payee_iban', 'payee_type', 'payee_recipient_name', 'payee_recipient_email',

            'transit_payee_id',
            'transit_funding_source_id',

            'additional_information',
            'documents',

            # we can use model properties as well
            'funder_payment_account_id',
            'funding_deadline',
            'balance',
            'initial_amount'
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
