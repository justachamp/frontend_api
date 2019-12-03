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

logger = logging.getLogger(__name__)


class EscrowStatus(Enum):
    pending = 'pending'  # escrow is waiting to be accepted
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

    def __str__(self):
        return "Escrow(id=%s, payee_id=%s, transit_wallet_id=%s, " \
               "transit_payee_id=%s, transit_funding_source_id=%s, " \
               "acceptance_deadline=%s, balance=%s)" % (
                   self.id, self.payee_id, self.wallet_id,
                   self.transit_payee_id, self.transit_funding_source_id,
                   self.funding_deadline, self.balance
               )

    @property
    def balance(self) -> int:
        # TODO: get balance from the corresponding VIRTUAL_WALLET(transit_wallet_id) ??
        return 0

    @property
    def initial_amount(self) -> int:
        # TODO: get initial amount from first 'request_funds' EscrowOperation ?
        return 0

    @property
    def funding_deadline(self) -> datetime:
        # TODO: find out _first_ LoadFunds EscrowOperation end return its 'approval_deadline'
        return arrow.utcnow()

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
        if self.status == EscrowStatus.stopped:
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


class EscrowOperationType(Enum):
    """
    All of theses operation types require mutual approval
    """
    request_funds = 'request_funds'  # Request of funds
    close_escrow = 'close_escrow'  # Request to close escrow
    create_escrow = 'create_escrow'  # Initial request to create escrow

    class Labels:
        request_funds = 'Request funds'
        close_escrow = 'Close escrow'
        create_escrow = 'Create escrow'


# support JSON schema versioning for possible future changes
def default_args_data_dict():
    return {'version': 1, 'args': {}}


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
        null=True
    )

    @staticmethod
    def get_operation_class(escrow_operation_type: EscrowOperationType):
        return {
            EscrowOperationType.close_escrow: CloseEscrowOperation,
            EscrowOperationType.request_funds: ReleaseFundsEscrowOperation
        }.get(escrow_operation_type)

    @property
    def additional_information(self):
        return self.args.get('args', {}).get('additional_information')

    @property
    def status(self):
        if self.approved:
            result = EscrowOperationStatus.approved
        elif self.is_expired or self.approved is False:
            result = EscrowOperationStatus.rejected
        else:
            result = EscrowOperationStatus.pending

        return result

    def accept(self, user):
        if self.approved is not None:
            raise ValidationError(f'Cannot accept escrow operation with current approved state (approved={self.approved})')

        if self.is_expired:
            raise ValidationError(f'Cannot accept expired escrow operation')

        self.approved = True
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) was approved" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

    def reject(self, user):
        if self.approved is not None:
            raise ValidationError(f'Cannot reject escrow operation with current approved state (approved={self.approved})')

        if self.is_expired:
            raise ValidationError(f'Cannot reject expired escrow operation')

        self.approved = False
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) was rejected" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

class EscrowOperationStatus(Enum):
    pending = 'pending'
    rejected = 'rejected'
    approved = 'approved'

    class Labels:
        pending = 'Pending'
        rejected = 'Rejected'
        approved = 'Approved'

class CreateEscrowOperation(EscrowOperation):
    def accept(self, user):
        super().accept(user)

        self.escrow.move_to_status(EscrowStatus.ongoing)

    class Meta:
        managed = False


class CloseEscrowOperation(EscrowOperation):
    def accept(self, user):
        super().accept(user)

        self.escrow.move_to_status(EscrowStatus.closed)

    class Meta:
        managed = False


class ReleaseFundsEscrowOperation(EscrowOperation):
    @property
    def amount(self):
        return self.args.amount

    def accept(self, user):
        super().accept(user)

        escrow = self.escrow
        funding_source_id = escrow.transit_funding_source_id
        payee_id = escrow.payee_id

        try:
            from frontend_api.core import client
            client.PaymentApiClient.create_payment(p=client.PaymentDetails(
                id=uuid4(),
                user_id=UUID(user.id),
                payment_account_id=UUID(user.account.payment_account_id),
                schedule_id=None,
                currency=Currency(escrow.currency),
                amount=self.amount,
                description=self.additional_information,
                payee_id=payee_id,
                funding_source_id=funding_source_id,
                parent_payment_id=None,
                execution_date=None
            ))

        except Exception:
            logger.error("Unable to create payment for ReleaseFundsEscrowOperation (id=%s) due to unknown error: %r. " % (
                self.id, format_exc()
            ), extra={
                'escrow_operation_id': self.id,
                'escrow_id': escrow.id
            })

    class Meta:
        managed = False
