from __future__ import annotations
import logging
from datetime import datetime
from traceback import format_exc
from typing import Dict, Union

from enumfields import EnumField
from uuid import UUID
import arrow
from django.core.serializers.json import DjangoJSONEncoder
from rest_framework.exceptions import ValidationError

from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.postgres.fields import JSONField

from core.models import Model, User
from core.fields import Currency, UserRole, PaymentStatusType, PayeeType
from customate.settings import ESCROW_OPERATION_APPROVE_DEADLINE
import external_apis.payment.service as payment_service

from frontend_api.fields import EscrowStatus, EscrowOperationType, EscrowOperationStatus

logger = logging.getLogger(__name__)


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

    def __repr__(self):
        return str(self)

    @property
    def initial_amount(self) -> int:
        """
        Initial amount is just an 'amount' from first 'LoadFunds' operation
        :return:
        """
        op = self.load_escrow_operation  # type: LoadFundsEscrowOperation
        logger.debug("op=%r" % op)
        return op.amount

    @property
    def funding_deadline(self) -> datetime:
        """
        Latest funding date of first 'LoadFunds' operation for this escrow
        :return:
        """
        op = self.load_escrow_operation  # type: LoadFundsEscrowOperation
        return op.approval_deadline or arrow.utcnow().datetime

    @property
    def closing_date(self) -> datetime:
        # We can assume that Escrow record will not be edited after moving to "Closed" state
        # OR we can add EscrowOperation.approved_date field to trace when "close_escrow" operation will be accepted
        return self.updated_at \
            if self.status in [EscrowStatus.closed, EscrowStatus.rejected, EscrowStatus.terminated] \
            else None

    @property
    def can_dispute(self) -> bool:
        """
        Can user dispute some operations on this Escrow?
        :return:
        """
        return self.status is EscrowStatus.ongoing

    @property
    def can_close(self) -> bool:
        """
        Can user issue 'CloseEscrow' operation on this Escrow?
        :return:
        """
        if self.status is not EscrowStatus.ongoing:
            return False

        op = self.close_escrow_operation
        if op is None:
            return True

        return op.status is not EscrowOperationStatus.pending

    @property
    def can_release_funds(self) -> bool:
        """
        Can user issue 'ReleaseFunds' operation on this Escrow?
        :return:
        """
        # Obviously, no money to release
        if self.balance == 0:
            return False

        if self.status is not EscrowStatus.ongoing:
            return False

        op = self.release_escrow_operation
        if op is not None and op.status is EscrowOperationStatus.pending:
            return False

        return True

    def has_pending_operations_for(self, user: User) -> bool:
        """
        Do we have any unapproved operations in current escrow which require actions from counterpart?
        :param user:
        :return:
        """
        # Avoiding returning True for scenario with just-created Escrow record: we have two operations here, and one of
        # them, "load_funds", could wait for action from funder, but only after recipient will approve
        # "create_escrow" operation
        if self.status in [EscrowStatus.pending, EscrowStatus.rejected] \
                and self.create_escrow_operation.creator.id == user.id:
            return False

        return EscrowOperation.objects.filter(
            escrow__id=self.id,
            # sharing knowledge about "status" field calculated fields - not good
            is_expired=False,
            approved=None
        ).exclude(creator=user).exists()

    @property
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

        # Check if escrow has status 'closed'
        # need to avoid documents handling for such schedules
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

    @property
    def load_escrow_operation(self) -> LoadFundsEscrowOperation or None:
        """
        Get the first and only LoadEscrow operation for this escrow
        :return:
        """
        return LoadFundsEscrowOperation.objects.filter(escrow__id=self.id).first()

    @property
    def create_escrow_operation(self) -> CreateEscrowOperation or None:
        """
        Get the first and only CreateEscrow operation for this escrow
        :return:
        """
        return CreateEscrowOperation.objects.filter(escrow__id=self.id).first()

    @property
    def close_escrow_operation(self) -> CloseEscrowOperation or None:
        """
        Get the last and only CloseEscrow operation for this escrow
        :return:
        """
        return CloseEscrowOperation.objects.filter(escrow__id=self.id).first()

    @property
    def release_escrow_operation(self) -> ReleaseFundsEscrowOperation or None:
        """
        Get the last and only ReleaseEscrow operation for this escrow
        :return:
        """
        return ReleaseFundsEscrowOperation.objects.filter(escrow__id=self.id).first()

    def accept(self):
        """
        Accept whole escrow by changing the status of underlying initial 'CreateEscrowOperation'
        :return:
        """
        self.create_escrow_operation.accept()

    def reject(self):
        """
        Reject whole Escrow by changing status of underlying CreateEscrow operation
        :return:
        """
        self.create_escrow_operation.reject()

    def update_balance(self, balance):
        """
        Track total balance of underlying money transactions here.
        :param balance:
        :return:
        """
        old_balance = self.balance
        self.balance = balance
        self.save(update_fields=["balance"])
        logger.info("Updated escrow (id=%s) balance=%d (was=%s)" % (self.id, balance, old_balance), extra={
            'escrow_id': self.id,
            'new_balance': balance,
            'old_balance': old_balance
        })


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
    def cast(op: EscrowOperation) -> Union[
        CreateEscrowOperation, CloseEscrowOperation,
        LoadFundsEscrowOperation, ReleaseFundsEscrowOperation
    ]:
        """
        Cast operation to its appropriate specific subclass.
        :param op:
        :return:
        """
        SubClass = {
            EscrowOperationType.create_escrow: CreateEscrowOperation,
            EscrowOperationType.close_escrow: CloseEscrowOperation,
            EscrowOperationType.load_funds: LoadFundsEscrowOperation,
            EscrowOperationType.release_funds: ReleaseFundsEscrowOperation
        }.get(op.type)

        if SubClass is None:
            raise ValidationError(f"Cannot find appropriate class for specified operation's type: {op.type}")

        # We need to create pre-filled sub-class object based on superclass object
        # https://stackoverflow.com/questions/4064808/django-model-inheritance-create-sub-instance-of-existing-instance-downcast
        result = SubClass()
        result.__dict__.update(op.__dict__)
        return result

    def get_arg(self, name, default_value=None):
        return self.args.get('args', {}).get(name, default_value)

    @property
    def pargs(self):
        return self.args.get('args', {})

    @pargs.setter
    def pargs(self, data: Dict):
        self.args['args'] = data

    @property
    def status(self) -> EscrowOperationStatus:
        if self.approved:
            result = EscrowOperationStatus.approved
        elif self.is_expired or self.approved is False:
            result = EscrowOperationStatus.rejected
        else:
            result = EscrowOperationStatus.pending

        return result

    @property
    def additional_information(self):
        return self.escrow.additional_information

    @property
    def requires_mutual_approval(self):
        """
        :return: whether or not this particular operation requires mutual approval from counterpart
        """
        return True

    def accept(self):
        """
        Accept this operation on behalf of current user
        :return:
        """
        if not self.approved is None:
            raise ValidationError(f'Cannot accept operation when approved={self.approved} is set already')

        if self.is_expired:
            raise ValidationError(f'Cannot accept operation when is_expired={self.is_expired}')

        self.approved = True
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) was approved" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

    def reject(self):
        """
        Reject this operation on behalf of current user
        :return:
        """
        if not self.approved is None:
            raise ValidationError(f'Cannot reject escrow operation when approved={self.approved} is set already')

        if self.is_expired:
            raise ValidationError(f'Cannot reject escrow operation when is_expired={self.is_expired}')

        self.approved = False
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) was rejected" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

    def reset_approved_state(self):
        """
        Reset "approved" flag for this operation, allowing user to repeat "acceptance" attempt
        :return:
        """
        self.approved = None
        self.save(update_fields=["approved"])
        logger.info("Escrow operation (id=%s) approved state was reset" % self.id, extra={
            'escrow_operation_id': self.id,
            'escrow_id': self.escrow.id
        })

    def __str__(self):
        return "EscrowOperation(id=%s, type=%s, escrow=%s, args=%s)" % (
            self.id, self.type.value, self.escrow.id if self.escrow else None, self.args
        )

    def __repr__(self):
        return str(self)


class CreateEscrowOperation(EscrowOperation):
    """
    Operation related to initial creation of Escrow by either party.
    """

    class Meta:
        proxy = True

    class TypedManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(type=EscrowOperationType.create_escrow).order_by("created_at")

    objects = TypedManager()  # The default manager

    def accept(self):
        super().accept()

        if self.escrow.wallet_id:
            logger.info("Skipping wallet creation as it exists already(wallet_id=%s)" % self.escrow.wallet_id)
            return

        wallet_details = payment_service.Wallet.create(
            currency=self.escrow.currency,
            payment_account_id=self.escrow.funder_payment_account_id
        )

        self.escrow.move_to_status(status=EscrowStatus.pending_funding)
        self.escrow.wallet_id = wallet_details.id
        self.escrow.transit_funding_source_id = wallet_details.funding_source_id
        self.escrow.transit_payee_id = wallet_details.payee_id
        self.escrow.save()

    def reject(self):
        super().reject()

        self.escrow.move_to_status(status=EscrowStatus.rejected)


class CloseEscrowOperation(EscrowOperation):
    """
    Close request of Escrow initiated by either party
    """

    class Meta:
        proxy = True

    class TypedManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(type=EscrowOperationType.close_escrow).order_by("-created_at")

    objects = TypedManager()  # The default manager

    def accept(self):
        super().accept()
        self.escrow.move_to_status(status=EscrowStatus.closed)

        self._refund_all_escrow_funds_to_funder()

        payment_service.Wallet.deactivate(self.escrow.wallet_id)
        payment_service.FundingSource.deactivate(self.escrow.transit_funding_source_id)
        payment_service.Payee.deactivate(self.escrow.transit_payee_id)

    def _refund_all_escrow_funds_to_funder(self):
        """
        Note that we cannot rely on Escrow.balance field here, because it's possible that we still didn't process
        latest "on_transaction_change" event and local "balance" field has incorrect value
        :return:
        """
        # Receiving latest wallet details ("balance" included)
        wallet_details = payment_service.Wallet.get(self.escrow.wallet_id)
        amount = wallet_details.balance
        funding_source_id = self.escrow.transit_funding_source_id
        payment_result = None
        description = "{escrow_name} funds release after closing".format(escrow_name=self.escrow.name)

        if amount <= 0:
            logger.info("There are no funds to release for Escrow (id=%s, op_id=%s)" % (self.escrow.id, self.id),
                        extra={'escrow_operation_id': self.id, 'escrow_id': self.escrow.id})
            return

        try:
            # Searching for appropriate funder's payee
            funder_wallet_payees = payment_service.Payee.find(self.escrow.funder_payment_account_id, PayeeType.WALLET,
                                                              self.escrow.currency)
            if isinstance(funder_wallet_payees, list) and len(funder_wallet_payees) > 1:
                raise ValidationError("Cannot process with releasing Escrows funds. Expected only one wallet's payee.")
            else:
                funder_wallet_payee_id = funder_wallet_payees[0].id

            # Sending money from Escrow's wallet (transit_funding_source_id) to
            # funder's "real" wallet (funder_wallet_payee_id)
            logger.info("Sending release funds payment for Escrow (id=%s)" % self.escrow.id)
            payment_result = payment_service.Payment.create(
                user_id=self.escrow.funder_user.id,
                payment_account_id=self.escrow.funder_payment_account_id,
                currency=Currency(self.escrow.currency),
                amount=amount,
                description=description,
                payee_id=funder_wallet_payee_id,
                funding_source_id=funding_source_id
            )

            logger.info("Release funds payment for Escrow (id=%s) status: %s" % (self.escrow.id, payment_result.status))
            if payment_result.status is PaymentStatusType.FAILED:
                raise ValidationError(payment_result.error_message)
        except ValidationError as ex:
            logger.warning("Release all Escrow funds payment for %s (op_id=%s) was created with FAILED status (%s)" % (
                type(self), self.id, payment_result
            ), extra={
                'escrow_operation_id': self.id,
                'escrow_id': self.escrow.id
            })
            raise ex
        except Exception:
            logger.error("Unable to create payment for %s (op_id=%s) due to unknown error: %r. " % (
                type(self), self.id, format_exc()
            ), extra={
                'escrow_operation_id': self.id,
                'escrow_id': self.escrow.id
            })
            raise ValidationError("Unable to accept operation(id=%s)" % self.id)

        logger.info("Finished with refunding all Escrow (id=%s) funds " % self.escrow.id)


class LoadFundsEscrowOperation(EscrowOperation):
    """
    Operation of loading of funds by Funder
    """

    class Meta:
        proxy = True

    class TypedManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(type=EscrowOperationType.load_funds).order_by("created_at")

    objects = TypedManager()  # The default manager

    @property
    def requires_mutual_approval(self):
        """
        We don't want to require approval from a counterpart if a funder decided to add funds to an Escrow
        :return: whether or not this particular operation requires mutual approval from counterpart
        """
        return not self.creator.id == self.escrow.funder_user.id

    @property
    def amount(self) -> int:
        """
        Arbitrary amount of money top-up for current Escrow
        :return:
        """
        return int(self.pargs["amount"])

    @amount.setter
    def amount(self, value: int):
        self.pargs["amount"] = value

    @property
    def funding_source_id(self) -> UUID:
        """
        Source of money to load Escrow wallet from
        :return:
        """
        return UUID(self.pargs["funding_source_id"])

    @funding_source_id.setter
    def funding_source_id(self, value: UUID):
        self.pargs["funding_source_id"] = str(value)

    def accept(self):
        super().accept()

        escrow = self.escrow
        payee_id = escrow.transit_payee_id
        description = "{escrow_name} funding".format(escrow_name=escrow.name)

        try:
            payment_service.Payment.create(
                user_id=escrow.funder_user.id,
                payment_account_id=escrow.funder_payment_account_id,
                currency=Currency(escrow.currency),
                amount=self.amount,
                description=description,
                payee_id=payee_id,
                funding_source_id=self.funding_source_id
            )
        except Exception:
            logger.error("Unable to create payment for %s (id=%s) due to unknown error: %r. " % (
                type(self), self.id, format_exc()
            ), extra={
                'escrow_operation_id': self.id,
                'escrow_id': escrow.id
            })
            raise ValidationError("Unable to accept operation(id=%s)" % self.id)


class ReleaseFundsEscrowOperation(EscrowOperation):
    """
    Request to release money by Receiver
    """

    class Meta:
        proxy = True

    class TypedManager(models.Manager):
        def get_queryset(self):
            return super().get_queryset().filter(type=EscrowOperationType.release_funds)

    objects = TypedManager()  # The default manager

    @property
    def requires_mutual_approval(self):
        """
        We don't want to require approval from a counterpart if a funder decided to release funds to receiver
        :return: whether or not this particular operation requires mutual approval from counterpart
        """
        return not self.creator.id == self.escrow.funder_user.id

    @property
    def amount(self) -> int:
        """
        Arbitrary amount of money withdrawal for current Escrow
        :return:
        """
        return int(self.pargs["amount"])

    @amount.setter
    def amount(self, value: int):
        self.pargs["amount"] = value

    def accept(self):
        super().accept()

        escrow = self.escrow
        funding_source_id = escrow.transit_funding_source_id
        payee_id = escrow.payee_id
        description = "{escrow_name} funds release".format(escrow_name=escrow.name)

        try:
            payment_service.Payment.create(
                user_id=escrow.funder_user.id,
                payment_account_id=escrow.funder_payment_account_id,
                currency=Currency(escrow.currency),
                amount=self.amount,
                description=description,
                payee_id=payee_id,
                funding_source_id=funding_source_id
            )
        except Exception:
            logger.error("Unable to create payment for %s (op_id=%s) due to unknown error: %r. " % (
                type(self), self.id, format_exc()
            ), extra={
                'escrow_operation_id': self.id,
                'escrow_id': escrow.id
            })
            raise ValidationError("Unable to accept operation(id=%s)" % self.id)
