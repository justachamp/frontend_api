import logging
from abc import abstractmethod
from datetime import datetime
from traceback import format_exc
from uuid import uuid4, UUID

from enumfields import Enum
from uuid import UUID
import arrow
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.exceptions import ValidationError

from enumfields import EnumField
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import JSONField

from core.models import Model, User
from core.fields import Currency, UserRole
from customate.settings import ESCROW_OPERATION_APPROVE_DEADLINE
from external_apis.payment.service import Payment

from external_apis.payment.service import Wallet

logger = logging.getLogger(__name__)


class EscrowStatus(Enum):
    pending = 'pending'  # escrow is waiting to be accepted
    pending_funding = 'pending_funding'  # escrow is waiting for initial funds
    ongoing = 'ongoing'  # escrow was accepted and request/load of funds ops are ongoing
    closed = 'closed'  # closed by mutual agreement of counterparts
    terminated = 'terminated'  # 'closed' automatically due to inaction of parties involved
    rejected = 'rejected'  # was rejected for some reason by either counterpart

    class Labels:
        pending = 'Pending'
        ongoing = 'Ongoing'
        closed = 'Closed'
        terminated = 'Terminated'
        rejected = 'Rejected'


class EscrowPurpose(Enum):
    receive = 'receive'
    pay = 'pay'

    class Labels:
        receive = 'Receive funds'
        pay = 'Pay funds'


class Escrow(Model):
    name = models.CharField(_('escrow name'), max_length=150)
    status = EnumField(EscrowStatus)
    funder_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        blank=False,
        related_name='%(class)s_funded_by_me'
    )  # type: User
    recipient_user = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        blank=True,
        null=True,
        related_name='%(class)s_recieved_by_me'
    )  # type: User
    currency = EnumField(Currency)

    wallet_id = models.UUIDField(
        help_text=_("Identifier of the virtual wallet, that relates to this Escrow"),
        default=None, blank=True, null=True
    )

    payee_id = models.UUIDField(
        # "Release money from Escrow" payment will include:
        # "origin" = transit_funding_source_id and "recipient" = payee_id
        help_text=_("Identifier of the recipient user wallet's payee, for payments from Escrow")
    )

    # Payee related fields are required for Escrow search
    payee_recipient_name = models.CharField(max_length=254, default='')
    payee_recipient_email = models.CharField(max_length=254, default='')
    payee_iban = models.CharField(max_length=50, default='')

    transit_funding_source_id = models.UUIDField(
        # "Release money from Escrow" payment will include:
        # "origin" = transit_funding_source_id and "recipient" = payee_id
        help_text=_(
            "Identifier of the transit 'blocked funds' virtual wallet's funding source, for payments from Escrow"),
        default=None, blank=True, null=True
    )
    transit_payee_id = models.UUIDField(
        # "Load money to Escrow" payment will include:
        # "origin" = any payer's funding source's id and "recipient" = transit_payee_id
        help_text=_("Identifier of the transit 'blocked funds' virtual wallet's payee, for payments to Escrow"),
        default=None, blank=True, null=True
    )

    additional_information = models.CharField(
        max_length=250,
        blank=True,
        null=True
    )

    balance = models.IntegerField(
        blank=True,
        null=True,
        help_text=_("Transit storage of balance from payment service.")
    )

    def __str__(self):
        return "Escrow(id=%s, payee_id=%s, transit_wallet_id=%s, " \
               "transit_payee_id=%s, transit_funding_source_id=%s, " \
               "acceptance_deadline=%s, balance=%s)" % (
                   self.id, self.payee_id, self.wallet_id,
                   self.transit_payee_id, self.transit_funding_source_id,
                   self.funding_deadline, self.balance
               )

    @property
    def initial_amount(self) -> int:
        # TODO: get initial amount from first 'request_funds' EscrowOperation ?

        operation = self._get_initial_load_funds_operation()
        if operation is not None:
            return operation.amount

        return 0

    @property
    def funding_deadline(self) -> datetime:
        operation = self._get_initial_load_funds_operation()
        if operation is not None:
            return operation.approval_deadline

        return arrow.utcnow().datetime

    @property
    def closing_date(self) -> datetime:
        # We can assume that Escrow record will not be edited after moving to "Closed" state
        # OR we can add EscrowOperation.approved_date field to trace when "close_escrow" operation will be accepted
        return self.updated_at if self.status is EscrowStatus.closed else None

    @property
    def can_close(self) -> bool:
        operation = self._get_latest_operation(EscrowOperationType.close_escrow)
        if operation is None:
            return True

        return operation.status is not EscrowOperationStatus.pending

    @property
    def can_release_funds(self) -> bool:
        operation = self._get_latest_operation(EscrowOperationType.release_funds)
        if operation is None:
            return True

        return operation.status is not EscrowOperationStatus.pending

    def has_pending_operations_for_user(self, user) -> bool:
        return EscrowOperation.objects.filter(
            escrow__id=self.id,
            # sharing knowledge about "status" field calculated fields - not good
            is_expired=False,
            approved=None
        ).exclude(creator=user).exists()

    def funder_payment_account_id(self) -> UUID:
        return self.funder_user.account.payment_account_id

    def allow_post_document(self, user: User) -> bool:
        """
        :param user:
        :return:
        """
        recipient = self.recipient_user
        # Check if recipient or sender have common account with user from request (or user's subusers)
        related_account_ids = user.get_all_related_account_ids()

        # Check if escrow has status 'stopped'
        #    need to avoid documents handling for such schedules
        if self.status == EscrowStatus.closed:
            return False

        if user.role == UserRole.owner:
            return (recipient and recipient.account.id in related_account_ids) \
                   or self.funder_user.account.id in related_account_ids

        return False

    def move_to_status(self, status: EscrowStatus):
        old_status = self.status
        self.status = status
        self.save(update_fields=["status"])
        logger.info("Updated escrow (id=%s) status=%s (was=%s)" % (self.id, status, old_status), extra={
            'escrow_id': self.id,
            'new_status': status,
            'old_status': old_status
        })

    def accept(self):
        operation = self._get_create_escrow_operation()
        if operation is None:
            raise ValidationError('Cannot find "Create" operation for Escrow (%s) acceptance' % self.id)

        EscrowOperation.get_specific_operation_obj(operation).accept()

    def _get_create_escrow_operation(self):
        try:
            return EscrowOperation.objects.filter(
                escrow__id=self.id,
                type=EscrowOperationType.create_escrow,
            ).order_by("created_at")[0:1].get()
        except EscrowOperation.DoesNotExist:
            return None

    def _get_initial_load_funds_operation(self):
        try:
            return EscrowOperation.objects.filter(
                escrow__id=self.id,
                type=EscrowOperationType.load_funds,
            ).order_by("created_at")[0:1].get()
        except EscrowOperation.DoesNotExist:
            return None

    def _get_latest_operation(self, operation_type):
        try:
            return EscrowOperation.objects.filter(
                escrow__id=self.id,
                type=operation_type,
            ).order_by("-created_at")[0:1].get()
        except EscrowOperation.DoesNotExist:
            return None

    def reject(self):
        operation = self._get_create_escrow_operation()
        if operation is None:
            raise ValidationError('Cannot find "Create" operation for Escrow (%s) rejection' % self.id)

        EscrowOperation.get_specific_operation_obj(operation).reject()

    def update_balance(self, balance):
        self.balance = balance
        self.save()


class EscrowOperationType(Enum):
    """
    All of theses operation types require mutual approval
    """
    load_funds = 'load_funds'  # Load funds
    request_funds = 'request_funds'  # Request of funds
    release_funds = 'release_funds'  # Release funds
    close_escrow = 'close_escrow'  # Request to close escrow
    create_escrow = 'create_escrow'  # Initial request to create escrow

    class Labels:
        load_funds = 'Load funds'
        request_funds = 'Request funds'
        release_funds = 'Release funds'
        close_escrow = 'Close escrow'
        create_escrow = 'Create escrow'


# support JSON schema versioning for possible future changes
def default_args_data_dict():
    return {'version': 1, 'args': {}}


class EscrowOperationStatus(Enum):
    pending = 'pending'
    rejected = 'rejected'
    approved = 'approved'

    class Labels:
        pending = 'Pending'
        rejected = 'Rejected'
        approved = 'Approved'


class EscrowOperation(Model):
    """
    Any operation that requires mutual approval from both parties
    """
    escrow = models.ForeignKey(
        Escrow,
        on_delete=models.DO_NOTHING,
        blank=False,
    )  # type: Escrow
    type = EnumField(EscrowOperationType)  # All possible operations on escrow
    # We need to store operation's creator, so that we can distinguish "my" and "others" records to correctly
    # react to them in UI (hide buttons, don't display "red dot" for Escrow etc.)
    creator = models.ForeignKey(
        User,
        on_delete=models.DO_NOTHING,
        blank=False,
        related_name='%(class)s_created_by_me'
    )  # type: User

    approved = models.BooleanField(
        default=None,
        null=True,
        help_text=_('current approval status'),
    )
    is_expired = models.BooleanField(
        default=False,
        help_text=_('if TRUE, this operation should NOT be considered for execution on Escrow'),
    )

    args = JSONField(
        encoder=DjangoJSONEncoder,
        default=default_args_data_dict,
        help_text=_("arbitrary set of operation arguments/values depending on 'type', for instance {'sum': 10}")
    )

    approval_deadline = models.DateField(
        help_text="Final deadline, after which the Operation is automatically expires",
        null=True,
        default=arrow.utcnow().shift(days=ESCROW_OPERATION_APPROVE_DEADLINE).datetime.date
    )

    @staticmethod
    def get_specific_operation_obj(operation):
        specific_operation_class = {
            EscrowOperationType.close_escrow: CloseEscrowOperation,
            EscrowOperationType.load_funds: LoadFundsEscrowOperation,
            EscrowOperationType.request_funds: ReleaseFundsEscrowOperation
        }.get(operation.type)

        return specific_operation_class.objects.get(id=operation.id)

    @property
    def additional_information(self):
        return self._get_args_property('additional_information')

    @property
    def amount(self):
        return self._get_args_property('amount', 0)

    def _get_args_property(self, name, default_value=None):
        return self.args.get('args', {}).get(name, default_value)

    def add_args(self, data: dict):
        self.args.get('args', {}).update(data)
        self.save(update_fields=["args"])

    @property
    def status(self):
        if self.approved:
            result = EscrowOperationStatus.approved
        elif self.is_expired or self.approved is False:
            result = EscrowOperationStatus.rejected
        else:
            result = EscrowOperationStatus.pending

        return result

    @property
    def requires_mutual_approval(self):
        """
        :return: whether or not this particular operation requires mutual approval from counterpart
        """
        return True

    def accept(self):
        if self.approved is not None:
            raise ValidationError(
                f'Cannot accept escrow operation with current approved state (approved={self.approved})')

        if self.is_expired:
            raise ValidationError(f'Cannot accept expired escrow operation')

        self.approved = True
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) was approved" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

    def reject(self):
        if self.approved is not None:
            raise ValidationError(
                f'Cannot reject escrow operation with current approved state (approved={self.approved})')

        if self.is_expired:
            raise ValidationError(f'Cannot reject expired escrow operation')

        self.approved = False
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) was rejected" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

    def __str__(self):
        return "EscrowOperation(id=%s, type=%s, escrow=%s, args=%s)" % (
            self.id, self.type, self.escrow.id if self.escrow else None, self.args
        )


class CreateEscrowOperation(EscrowOperation):
    class Meta:
        managed = False

    def accept(self):
        super().accept()

        payment_account_id = self.escrow.funder_user.account.payment_account_id
        wallet_details = Wallet.create(
            currency=self.escrow.currency,
            payment_account_id=payment_account_id
        )

        self.escrow.move_to_status(EscrowStatus.pending_funding)
        self.escrow.wallet_id = wallet_details.id
        self.escrow.transit_funding_source_id = wallet_details.funding_source_id
        self.escrow.transit_payee_id = wallet_details.payee_id
        self.escrow.save()


class CloseEscrowOperation(EscrowOperation):
    class Meta:
        managed = False

    def accept(self):
        super().accept()

        self.escrow.move_to_status(EscrowStatus.closed)


class LoadFundsEscrowOperation(EscrowOperation):
    class Meta:
        managed = False

    @property
    def requires_mutual_approval(self):
        """
        We don't want to require approval from a counterpart if a funder decided to add funds to an Escrow

        :return: whether or not this particular operation requires mutual approval from counterpart
        """
        return not self.creator.id == self.escrow.funder_user.id

    def accept(self):
        super().accept()

        escrow = self.escrow
        funding_source_id = self._get_args_property('source'),
        payee_id = escrow.transit_payee_id

        try:
            Payment.create(
                user_id=UUID(escrow.funder_user.id),
                payment_account_id=UUID(escrow.funder_user.account.payment_account_id),
                schedule_id=None,
                currency=Currency(escrow.currency),
                amount=self.amount,
                description=self.additional_information,
                payee_id=payee_id,
                funding_source_id=funding_source_id
            )
        except Exception:
            logger.error(
                "Unable to create payment for LoadFundsEscrowOperation (id=%s) due to unknown error: %r. " % (
                    self.id, format_exc()
                ), extra={
                    'escrow_operation_id': self.id,
                    'escrow_id': escrow.id
                })


class ReleaseFundsEscrowOperation(EscrowOperation):
    class Meta:
        managed = False

    @property
    def requires_mutual_approval(self):
        """
        We don't want to require approval from a counterpart if a funder decided to release funds to receiver

        :return: whether or not this particular operation requires mutual approval from counterpart
        """
        return not self.creator.id == self.escrow.funder_user.id

    def accept(self):
        super().accept()

        escrow = self.escrow
        funding_source_id = escrow.transit_funding_source_id
        payee_id = escrow.payee_id

        try:
            Payment.create(
                user_id=UUID(escrow.funder_user.id),
                payment_account_id=UUID(escrow.funder_user.account.payment_account_id),
                schedule_id=None,
                currency=Currency(escrow.currency),
                amount=self.amount,
                description=self.additional_information,
                payee_id=payee_id,
                funding_source_id=funding_source_id
            )
        except Exception:
            logger.error(
                "Unable to create payment for ReleaseFundsEscrowOperation (id=%s) due to unknown error: %r. " % (
                    self.id, format_exc()
                ), extra={
                    'escrow_operation_id': self.id,
                    'escrow_id': escrow.id
                })
