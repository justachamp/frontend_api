import logging
from datetime import datetime
from enumfields import Enum
from uuid import UUID
import arrow
from django.core.serializers.json import DjangoJSONEncoder

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
        help_text=_("Identifier of the virtual wallet, that relates to this Escrow")
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
            "Identifier of the transit 'blocked funds' virtual wallet's funding source, for payments from Escrow")
    )
    transit_payee_id = models.UUIDField(
        # "Load money to Escrow" payment will include:
        # "origin" = any payer's funding source's id and "recipient" = transit_payee_id
        help_text=_("Identifier of the transit 'blocked funds' virtual wallet's payee, for payments to Escrow")
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
