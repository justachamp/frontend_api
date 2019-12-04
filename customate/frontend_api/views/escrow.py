import logging
from traceback import format_exc
import arrow
from django.db.models import Q
from django.db import transaction
from django.utils.functional import cached_property
from django.shortcuts import get_object_or_404
from rest_framework.decorators import action
from rest_framework import status as status_codes
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.serializers import ValidationError

from core.models import User
from core import views
from core.exceptions import ConflictError
from core.fields import FundingSourceType

from frontend_api.fields import ScheduleStatus, SchedulePurpose
from frontend_api.core.client import PaymentApiClient
from frontend_api.models import Escrow, Document, EscrowOperation
from frontend_api.models.escrow import EscrowOperationType
from frontend_api.serializers import EscrowSerializer

from frontend_api.permissions import (
    HasParticularDocumentPermission,
    IsOwnerOrReadOnly,
    IsSuperAdminOrReadOnly,
    # SubUserManageSchedulesPermission,
    IsNotBlocked,
    IsActive,
    IsAccountVerified,
    # HasParticularSchedulePermission
)
from frontend_api.serializers.escrow import EscrowOperationSerializer

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
    ordering_fields = ('id', 'name', 'status')
    search_fields = ('name', 'payee_recipient_name', 'payee_recipient_email', 'payee_iban')

    filterset_fields = {
        # "exact" filter is excluded by framework, we can use alternative like "filter[currency.iexact]=GBP"
        'name': ('icontains', 'contains', 'iexact'),
        # 'payee_recipient_name': ('icontains', 'contains', 'iexact'),
        # 'payee_recipient_email': ('icontains', 'contains', 'iexact'),
        # 'payee_iban': ('icontains', 'contains', 'iexact'),
        'currency': ('iexact', 'in'),
        'funder_user__id': ('exact', ),
        'recipient_user__id': ('exact', ),
    }

    def get_serializer_class(self):
        # return UpdateScheduleSerializer if self.request.method == 'PATCH' else ScheduleSerializer
        return EscrowSerializer

    def get_queryset(self, *args, **kwargs):
        target_account_ids = self.request.user.get_all_related_account_ids()
        return Escrow.objects.filter(
            Q(funder_user__account__id__in=target_account_ids) | Q(recipient_user__account__id__in=target_account_ids)
        ).order_by('created_at')

    # @cached_property
    # def payment_client(self):
    #     return PaymentApiClient(self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create new Schedule / HTTP POST

        :param serializer:
        :return:
        """
        logger.info("Escrow creation, validated_data=%r" % serializer.validated_data)

        try:

            # counterpart_user_id = self.request.data.get("counterpart_user_id", None)
            # counterpart_user = User.objects.get(id=counterpart_user_id) if counterpart_user_id is not None else None

            # if purpose == SchedulePurpose.pay:
            #     origin_user = self.request.user
            #     recipient_user = counterpart_user
            # else:
            #     origin_user = counterpart_user
            #     recipient_user = self.request.user

            documents = serializer.validated_data.pop("documents", [])

            # schedule = serializer.save(
            #     status=status,
            #     funder_user=origin_user,
            #     recipient_user=recipient_user
            # )

            # logger.info("Successfully created new escrow record (id=%r)" % schedule.id)
            # serializer.assign_uploaded_documents_to_schedule(documents)


        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error("Unable to save Escrow=%r, due to %r" % (serializer.validated_data, format_exc()))
            raise ValidationError("Unable to save escrow")

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
        Handle HTTP DELETE here. We don't want to remove escrow record at all, instead we will create "close_escrow"
        EscrowOperation and will wait for approve from counterpart to process with Escrow's cancellation

        :param escrow:
        :return:
        """
        logger.info("Handle escrow destroy request")

        operation = EscrowOperation(
            escrow=escrow,
            type=EscrowOperationType.close_escrow,
            creator=self.request.user
        )
        operation.save()

        logger.info("Created %s" % operation)

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

        return Response()

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

        return Response()


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
        'escrow__id': ('exact', ),
        'type': ('in', ),
    }

    def get_queryset(self, *args, **kwargs):
        target_account_ids = self.request.user.get_all_related_account_ids()
        return EscrowOperation.objects.filter(
            Q(escrow__funder_user__account__id__in=target_account_ids)
            | Q(escrow__recipient_user__account__id__in=target_account_ids)
        ).order_by('created_at')

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

        escrow_operation_id = pk

        try:
            escrow_operation = EscrowOperation.objects.get(id=escrow_operation_id)
        except Exception:
            raise NotFound(f'EscrowOperation not found {escrow_operation_id}')

        return EscrowOperation.get_specific_operation_obj(escrow_operation).accept(request.user)

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
            operation = EscrowOperation.objects.get(id=operation_id)
        except Exception:
            raise NotFound(f'EscrowOperation not found {operation_id}')

        return EscrowOperation.get_specific_operation_obj(operation).reject(request.user)
