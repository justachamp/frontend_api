import logging
from traceback import format_exc
from uuid import UUID
from django.db.models import Q
from django.db import transaction, IntegrityError
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework import status as status_codes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError

from core.models import User
from core import views

from frontend_api.models.document import Document
from frontend_api.fields import EscrowOperationType
from frontend_api.models.escrow import Escrow
from frontend_api.models.escrow import EscrowOperation, CreateEscrowOperation, LoadFundsEscrowOperation

from frontend_api.serializers import EscrowSerializer

from frontend_api.permissions import (
    HasParticularDocumentPermission,
    IsOwnerOrReadOnly,
    IsSuperAdminOrReadOnly,
    # SubUserManageSchedulesPermission,
    IsNotBlocked,
    IsActive,
    IsAccountVerified,
    # HasParticularSchedulePermission,
)
from frontend_api.serializers.escrow import EscrowOperationSerializer

from frontend_api.notifications.escrows import (
    notify_counterpart_about_new_escrow,
    notify_originator_about_escrow_state,
    notify_about_requesting_action_with_funds,
    notify_about_fund_escrow_state,
    notify_about_declined_operation_request,
    notify_about_requesting_close_escrow
)

logger = logging.getLogger(__name__)


class EscrowViewSet(views.ModelViewSet):
    queryset = Escrow.objects.all()
    serializer_class = EscrowSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsAccountVerified,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly
                          # SubUserManageSchedulesPermission,
                          # HasParticularSchedulePermission
                          )

    # Example: /api/v1/escrows/?page[number]=1&filter[currency.iexact]=EUR&filter[name.icontains]=test&sort=-status
    ordering_fields = ('id', 'name', 'status', 'created_at')
    search_fields = ('name', 'payee_recipient_name', 'payee_recipient_email', 'payee_iban')

    filterset_fields = {
        # "exact" filter is excluded by framework, we can use alternative like "filter[currency.iexact]=GBP"
        'name': ('icontains', 'contains', 'iexact'),
        # 'payee_recipient_name': ('icontains', 'contains', 'iexact'),
        # 'payee_recipient_email': ('icontains', 'contains', 'iexact'),
        # 'payee_iban': ('icontains', 'contains', 'iexact'),
        'currency': ('iexact', 'in'),
        'funder_user__id': ('exact',),
        'recipient_user__id': ('exact',),
    }

    def get_serializer_class(self):
        # return UpdateScheduleSerializer if self.request.method == 'PATCH' else ScheduleSerializer
        return EscrowSerializer

    def get_queryset(self, *args, **kwargs):
        target_account_ids = self.request.user.get_all_related_account_ids()
        return Escrow.objects.filter(
            Q(funder_user__account__id__in=target_account_ids) | Q(recipient_user__account__id__in=target_account_ids)
        ).order_by('created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create new Escrow / HTTP POST

        :param serializer:
        :return:
        """
        logger.info("Escrow creation, validated_data=%r" % serializer.validated_data)

        funding_deadline = self.request.data.pop("funding_deadline", None)
        initial_amount = self.request.data.pop("initial_amount", None)

        if not all([funding_deadline, initial_amount]):
            raise ValidationError("'funding_deadline' and 'initial_amount' fields are required.")

        funder_user = get_object_or_404(User, id=self.request.data.get("funder_user_id"))  # type: User
        recipient_user = get_object_or_404(User, id=self.request.data.get("recipient_user_id"))  # type: User
        documents = serializer.validated_data.pop("documents", [])

        try:
            if serializer.is_valid(raise_exception=True):
                escrow = serializer.save(
                    funder_user=funder_user,
                    recipient_user=recipient_user
                )  # type: Escrow
                logger.info("Successfully created new escrow record (id=%r)" % escrow.id)
                serializer.assign_uploaded_documents_to_escrow(documents)
            else:
                raise ValidationError("Got invalid data for Escrow")
        except ValidationError as e:
            logger.info("Validation error. %r" % format_exc())
            raise e
        except Exception as e:
            logger.error("Unable to save Escrow=%r, due to %r" % (serializer.validated_data, format_exc()))
            raise ValidationError("Unable to save escrow")

        # Create initial operations:  Create Escrow Operation, Load Funds Operation
        # CreateEscrow
        logger.info("Creating CreateEscrowOperation for escrow_id=%s" % escrow.id)
        creator = self.request.user
        create_op = CreateEscrowOperation(
            escrow=escrow,
            type=EscrowOperationType.create_escrow,
            creator=creator,
            approval_deadline=funding_deadline
        )
        create_op.save()

        # LoadFunds
        logger.info("Creating LoadFundsEscrowOperation for escrow_id=%s" % escrow.id)
        load_funds_op = LoadFundsEscrowOperation(
            escrow=escrow,
            type=EscrowOperationType.load_funds,
            # Initial LoadFunds operation is always a pending operation for funder, so it should be created by recipient
            creator=recipient_user,
            approval_deadline=funding_deadline
        )
        load_funds_op.amount = initial_amount
        load_funds_op.save()

        # Send appropriate notification to counterpart
        counterpart = escrow.recipient_user if creator.id == escrow.funder_user.id else escrow.funder_user
        notify_counterpart_about_new_escrow(counterpart=counterpart, create_op=create_op, load_funds_op=load_funds_op)

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Update Escrow / HTTP PATCH

        :param serializer:
        :return:
        """
        logger.info("Handle escrow update request")

    def perform_destroy(self, escrow: Escrow):
        """
        Handle HTTP DELETE here.
        We don't want to remove escrow record at all
        :param escrow:
        :return:
        """
        logger.info("Handle escrow destroy request")
        raise ValidationError("Escrow record cannot be removed")

    @action(methods=['DELETE'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, HasParticularDocumentPermission
            ))
    def documents(self, request, pk):
        """
        The method for removing document objects from database.
        """
        key = request.query_params.get("key")
        if not key:
            logger.error("The 'key' parameter has not been passed %r" % format_exc())
            raise ValidationError("The 'key' parameter is required")
        document = get_object_or_404(Document, key=key)
        document.move_to_archive()
        logger.info("Document moved to archive. (Username: %s, Escrow id: %s, Document id: %s.)" % (
            request.user.username, document.escrow.id if document.escrow else None, document.id
        ))
        return Response(None, status=204)

    @transaction.atomic
    @action(methods=['POST'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly)
            )
    def accept(self, request, pk=None):
        """
        Used to accept an Escrow
        :param request:
        :param pk:
        :return:
        """
        escrow_id = pk
        try:
            escrow = Escrow.objects.get(id=escrow_id)
        except Exception:
            raise NotFound(f'Escrow not found {escrow_id}')
        escrow.accept()
        # Send appropriate notification to escrows creator.
        try:
            create_escrow_op = escrow.create_escrow_operation
            counterpart = self.request.user
            notify_originator_about_escrow_state(
                counterpart=counterpart,
                escrow_op=create_escrow_op,
                tpl_filename="notifications/escrow_accepted_by_counterpart.html"
            )
        except AssertionError:
            logger.error("Send notification about accepted escrow.\
                        Could not get initial CreateEscrowOperation. Escrow id: %s" % escrow.id)
            pass
        return Response(status=status_codes.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(methods=['POST'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly)
            )
    def reject(self, request, pk=None):
        """
        Used to reject an Escrow
        :param request:
        :param pk:
        :return:
        """
        escrow_id = pk
        try:
            escrow = Escrow.objects.get(id=escrow_id)
        except Exception:
            raise NotFound(f'Escrow not found {escrow_id}')
        escrow.reject()
        # Send appropriate notification to escrows creator.
        try:
            create_escrow_op = escrow.create_escrow_operation
            counterpart = self.request.user
            notify_originator_about_escrow_state(
                counterpart=counterpart,
                escrow_op=create_escrow_op,
                tpl_filename="notifications/request_rejected_by_counterpart.html"
            )
        except AssertionError:
            logger.error("Send notification about rejected escrow.\
                         Could not get initial CreateEscrowOperation. Escrow id: %s" % escrow.id)
            pass
        return Response(status=status_codes.HTTP_204_NO_CONTENT)


class EscrowOperationViewSet(views.ModelViewSet):
    queryset = EscrowOperation.objects.all()
    serializer_class = EscrowOperationSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsAccountVerified,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly
                          )

    filterset_fields = {
        'escrow__id': ('exact',),
        'type': ('in',),
    }

    def get_queryset(self, *args, **kwargs):
        target_account_ids = self.request.user.get_all_related_account_ids()
        return EscrowOperation.objects.filter(
            Q(escrow__funder_user__account__id__in=target_account_ids)
            | Q(escrow__recipient_user__account__id__in=target_account_ids)
        ).order_by('created_at')

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create new EscrowOperation / HTTP POST

        :param serializer:
        :return:
        """
        logger.info("EscrowOperation creation, validated_data=%r" % serializer.validated_data)

        # Check if operations Escrow has pending payment operations.
        escrow = get_object_or_404(Escrow, id=serializer.validated_data['escrow_id'])
        if escrow.has_pending_payment:
            raise ValidationError("Operation is not allowed while previous operation has not completed.")

        try:
            if serializer.is_valid(raise_exception=True):
                operation = serializer.save(creator=self.request.user)  # type: EscrowOperation
                logger.info("Successfully created new escrow operation (%r)" % operation)

                operation = EscrowOperation.cast(operation)

                # auto accept operation if it does not require any action from counterpart!
                if not operation.requires_mutual_approval:
                    operation.accept()

                # Notify funder about propose to load_funds/release_funds/close_escrow
                tpl_filenames = {
                    EscrowOperationType.load_funds: "notifications/requesting_funding_escrow.html",
                    EscrowOperationType.release_funds: "notifications/requesting_release_funds.html",
                }
                if self.request.user == operation.escrow.recipient_user and operation.type in tpl_filenames.keys():
                    logger.info("Start notify funder about requesting to fund/release funds. \
                                Funds recipient: %s. " % self.request.user)
                    notify_about_requesting_action_with_funds(
                        counterpart=self.request.user,
                        operation=operation,
                        tpl_filename=tpl_filenames[operation.type]
                    )
                if operation.requires_mutual_approval and operation.type == EscrowOperationType.close_escrow:
                    escrow = operation.escrow
                    request_recipient = escrow.recipient_user if operation.creator.id == escrow.funder_user.id else escrow.funder_user
                    notify_about_requesting_close_escrow(
                        request_recipient=request_recipient,
                        operation=operation,
                        tpl_filename="notifications/requesting_close_escrow.html"
                    )

        except ValidationError as e:
            logger.info("Invalid EscrowOperationSerializer error. %r" % format_exc())
            raise e
        except IntegrityError as e:
            # We allow to create several pending "load_funds" operations, all other operation types in "pending" state
            # should be present in one copy (this restriction is implemented on database level)
            logger.error("Unable to save EscrowOperation=%r, due to IntegrityError: %r" % (
                serializer.validated_data, format_exc()))
            raise ValidationError("Looks like counterpart has already performed some action with this Escrow record. "
                                  "Please refresh page and try again.")
        except Exception as e:
            logger.error("Unable to save EscrowOperation=%r, due to %r" % (serializer.validated_data, format_exc()))
            raise ValidationError("Unable to save escrow operation")

    @transaction.atomic
    @action(methods=['POST'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly)
            )
    def accept(self, request, pk=None):
        """
        Used to accept an Escrow operation by counterpart
        :param request:
        :param pk:
        :return:
        """
        op_id = pk
        try:
            operation = EscrowOperation.objects.get(id=op_id)  # type: EscrowOperation
        except Exception:
            raise NotFound(f'EscrowOperation not found {op_id}')

        logger.info("Accepting operation=%r, req_data=%r" % (operation, request.POST))

        if operation.type is EscrowOperationType.load_funds:
            op = EscrowOperation.cast(operation)  # type: LoadFundsEscrowOperation
            # Looks like we only need to set "funding_source_id". "amount" field is already set by EscrowOperation's
            # creator and we don't want to allow to change it in any way.
            op.funding_source_id = UUID(request.data["funding_source_id"])
            op.save()
        else:
            op = EscrowOperation.cast(operation)  # type: Union[CloseEscrowOperation, ReleaseFundsEscrowOperation]

        op.accept()
        return Response(status=status_codes.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(methods=['POST'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly)
            )
    def reject(self, request, pk=None):
        """
        Used to reject an Escrow operation by counterpart
        :param request:
        :param pk:
        :return:
        """
        operation_id = pk
        try:
            operation = EscrowOperation.objects.get(id=operation_id)  # type: EscrowOperation
            op = EscrowOperation.cast(operation)  # type: EscrowOperation
        except Exception:
            raise NotFound(f'EscrowOperation not found {operation_id}')

        op.reject()
        # Notify recipient user about rejected load_funds/close_escrow operation
        escrow = op.escrow
        current_user = self.request.user
        
        if all([op.creator == escrow.recipient_user,
                op.creator != current_user,
                op.type == EscrowOperationType.load_funds]):
            notify_about_fund_escrow_state(escrow=escrow)

        if op.type == EscrowOperationType.close_escrow:
            counterpart = escrow.recipient_user if op.creator.id == escrow.funder_user.id else escrow.funder_user
            notify_originator_about_escrow_state(
                counterpart=counterpart,
                escrow_op=op,
                tpl_filename="notifications/request_rejected_by_counterpart.html"
            )

        return Response(status=status_codes.HTTP_204_NO_CONTENT)
