import logging
from typing import Dict
from uuid import UUID
from traceback import format_exc

from rest_framework.serializers import ValidationError
from rest_framework.fields import BooleanField
from rest_framework_json_api.serializers import HyperlinkedModelSerializer, SerializerMethodField, JSONField

from core.models import User
from core.fields import Currency, SerializerField
import external_apis.payment.service as payment_service

from frontend_api.models.escrow import Escrow, EscrowOperationType, EscrowOperation, EscrowOperationStatus
from frontend_api.models.escrow import LoadFundsEscrowOperation, ReleaseFundsEscrowOperation
from frontend_api.fields import EscrowStatus

from frontend_api.models.document import Document
from frontend_api.serializers.document import DocumentSerializer
from frontend_api.serializers import (
    UUIDField,
    EnumField,
    CharField,
)

logger = logging.getLogger(__name__)


class BaseEscrowSerializer(HyperlinkedModelSerializer):

    def validate_payee_related_fields(self, payee_id: UUID) -> Dict:
        """
        We will try to receive some additional information (iban, title etc.) about payee from Payment API,
        and initialize appropriate fields in escrow's data
        :param payee_id:
        """
        response = {}
        if not payee_id:
            return response
        try:
            pd = payment_service.Payee.get(payee_id=payee_id)
        except Exception as e:
            logger.error("Got empty 'payee_id' or 'payee_details'. Payee_id: %s. %r", (payee_id, format_exc()))
            raise ValidationError("Payment service is not available. Try again later.")

        response.update({
            'payee_recipient_name': pd.recipient_name,
            'payee_recipient_email': pd.recipient_email,
            'payee_iban': pd.iban
        })

        return response

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
        raise NotImplemented()


class EscrowSerializer(BaseEscrowSerializer):
    name = CharField(required=True)
    status = EnumField(enum=EscrowStatus, default=EscrowStatus.pending, required=False)

    # Funder
    funder_user_id = UUIDField(required=True)
    # Recipient
    recipient_user_id = UUIDField(required=True)
    currency = EnumField(enum=Currency, required=True)

    # Allowed operations for current user
    can_dispute = BooleanField(required=False, read_only=True)
    can_close = BooleanField(required=False, read_only=True)
    can_release_funds = BooleanField(required=False, read_only=True)
    can_review_operations = BooleanField(required=False, read_only=True)
    can_review_transactions = BooleanField(required=False, read_only=True)
    can_accept = SerializerMethodField()
    can_load_funds = SerializerMethodField()

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

    purpose = SerializerMethodField()
    counterpart_email = SerializerMethodField()
    counterpart_name = SerializerMethodField()
    has_pending_operations = SerializerMethodField()

    class Meta:
        model = Escrow
        fields = (
            'name',
            'status',
            'funder_user_id',
            'recipient_user_id',
            'currency',
            'balance',
            'wallet_id',

            'payee_id',
            'payee_iban',
            'payee_recipient_name',
            'payee_recipient_email',

            'transit_payee_id',
            'transit_funding_source_id',

            'additional_information',
            'documents',

            'counterpart_email',
            'counterpart_name',
            'purpose',

            # we can use any model properties/callables as well
            # https://www.django-rest-framework.org/api-guide/serializers/#specifying-fields-explicitly
            'initial_amount',
            'funding_deadline',
            'funder_payment_account_id',
            'closing_date',

            'can_dispute',
            'can_accept',
            'can_close',
            'can_load_funds',
            'can_release_funds',
            'can_review_operations',
            'can_review_transactions',
            'has_pending_operations'
        )

    def get_can_accept(self, escrow: Escrow) -> bool:
        """
        We don't save information about Escrow's creator, but EscrowOperation record contains all necessary data and we
        base our calculations on it

        :param escrow:
        :return: whether or not this Escrow could be accepted by current user
        """
        return escrow.status == EscrowStatus.pending and self.get_has_pending_operations(escrow)

    def get_can_load_funds(self, escrow: Escrow) -> bool:
        """
        :param escrow:
        :return: whether or not current user can perform load funds to an Escrow
        """
        if escrow.has_pending_payment:
            return False
        latest_op = LoadFundsEscrowOperation.objects.filter(escrow__id=escrow.id).order_by("-created_at").first()
        current_user = self.context.get('request').user

        case = False
        case2 = False

        # We allow LoadFunds operation in two cases:
        # 1) it's a funder and an Escrow in "pending_funding" state and existing LoadFunds operation is not approved yet
        if current_user.id == escrow.funder_user.id:
            case = escrow.status is EscrowStatus.pending_funding \
                   and latest_op.status is not EscrowOperationStatus.approved

        # 2) Escrow in "ongoing" state and there is no existing pending LoadFunds operations
        if escrow.status is EscrowStatus.ongoing:
            case2 = latest_op.status is not EscrowOperationStatus.pending

        return case or case2

    def counterpart(self, escrow: Escrow):
        """
        Return correct counterpart based on user that performed the request
        :param escrow: Escrow
        :return counterpart: User
        """
        current_user = self.context.get('request').user  # type: User
        return escrow.recipient_user if current_user.id == escrow.funder_user.id else escrow.funder_user

    def get_counterpart_email(self, escrow: Escrow) -> str:
        """
        :param escrow: Escrow
        :return counterpart's email: str
        """
        return self.counterpart(escrow).email

    def get_counterpart_name(self, escrow: Escrow) -> str:
        """
        :param escrow: Escrow
        :return counterpart's name: str
        """
        counterpart = self.counterpart(escrow)
        return '%s %s' % (counterpart.first_name, counterpart.last_name)

    def get_purpose(self, escrow: Escrow) -> str:
        """
        Get escrow's purpose for current user

        :param escrow: Escrow
        :return Escrow's purpose: str
        """
        current_user = self.context.get('request').user
        return 'pay' if current_user.id == escrow.funder_user.id else 'receive'

    def get_has_pending_operations(self, escrow: Escrow) -> bool:
        current_user = self.context.get('request').user
        return escrow.has_pending_operations_for(user=current_user)

    def validate_name(self, value):
        """
        Make sure we avoid duplicate names for the same user.
        :param value:
        :return:
        """
        request = self.context.get('request')
        logger.info("Validate_name: %r, user=%r" % (value, request.user))

        target_account_ids = request.user.get_all_related_account_ids()
        queryset = Escrow.objects.filter(name=value, funder_user__account__id__in=target_account_ids) | \
                   Escrow.objects.filter(name=value, recipient_user__account__id__in=target_account_ids)

        entries_count = queryset.count()
        if entries_count >= 1:
            # NOTE: no need to provide {"fieldname": "error message"} inside magic validate_{fieldname} methods!
            raise ValidationError("Escrow with such name already exists")
        return value

    def assign_uploaded_documents_to_escrow(self, documents):
        logger.info("Assigned documents to escrow: %s" % self.instance.id)
        Document.objects.filter(key__in=[item["key"] for item in documents]).update(escrow=self.instance)


# Could be split into two serializer, one of which will be used for POST end-point and
# will include fields that should not be returned for GET details request (like raw "args")
class EscrowOperationSerializer(HyperlinkedModelSerializer):
    type = EnumField(enum=EscrowOperationType, required=True)
    status = EnumField(
        enum=EscrowOperationStatus,
        default=EscrowOperationStatus.pending,
        required=False,
        read_only=True
    )
    escrow_id = UUIDField(required=True)
    additional_information = CharField(required=False, read_only=True)
    amount = SerializerMethodField()
    is_action_required = SerializerMethodField()
    args = JSONField(required=False)

    class Meta:
        model = EscrowOperation
        fields = (
            'created_at',
            'type',
            'escrow_id',
            'additional_information',
            'amount',
            'status',
            'is_action_required',
            'args'
        )

    def get_amount(self, op: EscrowOperation) -> int or None:
        """
        Get amount or None if not applicable to current operation
        :param op:
        :return:
        """
        if op.type in [EscrowOperationType.load_funds, EscrowOperationType.release_funds]:
            sop = EscrowOperation.cast(op)  # type: Union[LoadFundsEscrowOperation, ReleaseFundsEscrowOperation]
            return sop.amount
        return None

    def get_is_action_required(self, op: EscrowOperation) -> bool:
        """
        Whether this EscrowOperation requires some action from current user.
        #We need to require actions only from operation's counterpart user

        :param op: EscrowOperation
        :return:
        """
        current_user = self.context.get('request').user

        # no action required for creators
        if op.creator.id == current_user.id:
            return False

        # if operation requires approval, verify that it wasn't given
        if op.requires_mutual_approval:
            return op.status is EscrowOperationStatus.pending
