import logging
from traceback import format_exc
import arrow
import celery
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
from customate.settings import CELERY_BEAT_SCHEDULE, FIRST_PAYMENTS_MIN_EXECUTION_DELAY

from frontend_api.fields import ScheduleStatus, SchedulePurpose
from frontend_api.tasks.payments import make_overdue_payment, make_payment, make_failed_payment
from frontend_api.core.client import PaymentApiClient
from frontend_api.models import Schedule, Document
from frontend_api.helpers import invite_payer

from frontend_api.permissions import (
    HasParticularDocumentPermission,
    IsOwnerOrReadOnly,
    IsSuperAdminOrReadOnly,
    SubUserManageSchedulesPermission,
    IsNotBlocked,
    IsActive,
    IsAccountVerified,
    HasParticularSchedulePermission)

from frontend_api.serializers.schedule import ScheduleSerializer, ScheduleAcceptanceSerializer, UpdateScheduleSerializer

logger = logging.getLogger(__name__)

SCHEDULES_START_PROCESSING_TIME = CELERY_BEAT_SCHEDULE["once_per_day"]["schedule"]  # type: celery.schedules.crontab


class ScheduleViewSet(views.ModelViewSet):
    queryset = Schedule.objects.all()
    serializer_class = ScheduleSerializer
    permission_classes = (IsAuthenticated,
                          IsActive,
                          IsNotBlocked,
                          IsAccountVerified,
                          IsSuperAdminOrReadOnly |
                          IsOwnerOrReadOnly |
                          SubUserManageSchedulesPermission,
                          HasParticularSchedulePermission)

    # Example: /api/v1/schedules/?page[number]=1&filter[currency.iexact]=EUR&filter[name.icontains]=test&sort=-status
    ordering_fields = ('id', 'name', 'status')
    search_fields = ('name', 'payee_recipient_name', 'payee_recipient_email', 'payee_iban')

    filterset_fields = {
        # "exact" filter is excluded by framework, we can use alternative like "filter[currency.iexact]=GBP"
        'name': ('icontains', 'contains', 'iexact'),
        'payee_title': ('icontains', 'contains', 'iexact'),
        'payee_recipient_name': ('icontains', 'contains', 'iexact'),
        'payee_recipient_email': ('icontains', 'contains', 'iexact'),
        'payee_iban': ('icontains', 'contains', 'iexact'),
        'currency': ('iexact', 'in'),
    }

    def get_serializer_class(self):
        return UpdateScheduleSerializer if self.request.method == 'PATCH' else ScheduleSerializer

    def get_queryset(self, *args, **kwargs):
        target_account_ids = self.request.user.get_all_related_account_ids()
        return Schedule.objects.filter(
            Q(origin_user__account__id__in=target_account_ids) | Q(recipient_user__account__id__in=target_account_ids)
        )

    @cached_property
    def payment_client(self):
        return PaymentApiClient(self.request.user)

    @transaction.atomic
    def perform_create(self, serializer):
        """
        Create new Schedule / HTTP CREATE

        :param serializer:
        :return:
        """
        logger.info("Handle schedule creation request")

        try:
            counterpart_user_id = self.request.data.get("counterpart_user_id", None)
            counterpart_user = User.objects.get(id=counterpart_user_id) if counterpart_user_id is not None else None
            purpose = serializer.validated_data["purpose"]
            status = ScheduleStatus.pending if purpose == SchedulePurpose.receive else ScheduleStatus.open

            if purpose == SchedulePurpose.pay:
                origin_user = self.request.user
                recipient_user = counterpart_user
            else:
                origin_user = counterpart_user
                recipient_user = self.request.user

            documents = serializer.validated_data.pop("documents", [])
            logger.info("Some initial schedule's attributes: counterpart_user_id=%s, status=%s"
                        % (counterpart_user_id, status))
            schedule = serializer.save(
                status=status,
                origin_user=origin_user,
                recipient_user=recipient_user
            )
            logger.info("Successfully created new schedule record (id=%r)" % schedule.id)
            serializer.assign_uploaded_documents_to_schedule(documents)

            if not schedule.have_time_for_nearest_payments_processing_by_scheduler \
                    and not schedule.have_time_for_first_payments_processing_manually:
                raise ConflictError(f'Cannot process first payments for schedule ({schedule.id})')

            self._process_first_payments_manually(schedule)

        except ValidationError as e:
            raise e
        except Exception as e:
            logger.error("Unable to save Schedule=%r, due to %r" % (serializer.validated_data, format_exc()))
            raise ValidationError("Unable to save schedule")

        # invite another customate user to pay
        if schedule.status is ScheduleStatus.pending and schedule.purpose is SchedulePurpose.receive:
            invite_payer(schedule=schedule)

    def _process_first_payments_manually(self, schedule):
        """
        Immediately create payments if scheduler will not be started today anymore, but deposit or first
        regular payment must be executed today.

        :param schedule:
        :return:
        """
        logger.info("Processing first payments manually if needed")
        user = self.request.user
        scheduler_start_date = schedule.nearest_scheduler_processing_date()
        current_date = arrow.utcnow().datetime.date()
        logger.debug("Verifying if schedule already run (scheduler_start_date=%s, now=%s)"
                     % (scheduler_start_date, arrow.utcnow()))

        if scheduler_start_date > current_date:
            logger.info("Scheduler will not be run today anymore, verifying deposit & regular scheduled dates.")
            # background celerybeatd service has already started payment processing
            # and missed first payment date which is now, therefore we initiate payments here
            if schedule.deposit_payment_scheduled_date == current_date:
                logger.info("Submitting deposit payment for schedule_id=%s (delay=%s)"
                            % (schedule.id, FIRST_PAYMENTS_MIN_EXECUTION_DELAY))
                # initiate one-off deposit payment
                make_payment.apply_async(
                    # It's possible that payment creation task will start execution before schedule creation
                    # transaction will be committed, it will cause problems for SchedulePayment record
                    countdown=FIRST_PAYMENTS_MIN_EXECUTION_DELAY,
                    kwargs={
                        'user_id': str(user.id),
                        'payment_account_id': str(schedule.origin_payment_account_id),
                        'schedule_id': str(schedule.id),
                        'currency': str(schedule.currency.value),
                        'payment_amount': int(schedule.deposit_amount),  # NOTE: deposit amount here!
                        'additional_information': str(schedule.deposit_additional_information),
                        'payee_id': str(schedule.payee_id),
                        'funding_source_id': str(schedule.funding_source_id),
                        'is_deposit': True
                    }
                )

            if schedule.first_payment_scheduled_date == current_date:
                logger.info("Submitting first payment for schedule_id=%s (delay=%s)"
                            % (schedule.id, FIRST_PAYMENTS_MIN_EXECUTION_DELAY))
                make_payment.apply_async(
                    # It's possible that payment creation task will start execution before schedule creation
                    # transaction will be committed, it will cause problems for SchedulePayment record
                    countdown=FIRST_PAYMENTS_MIN_EXECUTION_DELAY,
                    kwargs={
                        'user_id': str(user.id),
                        'payment_account_id': str(schedule.origin_payment_account_id),
                        'schedule_id': str(schedule.id),
                        'currency': str(schedule.currency.value),
                        'payment_amount': int(schedule.payment_amount),  # NOTE: regular amount
                        'additional_information': str(schedule.additional_information),
                        'payee_id': str(schedule.payee_id),
                        'funding_source_id': str(schedule.funding_source_id)
                    }
                )

    @transaction.atomic
    def perform_update(self, serializer):
        """
        Update Schedule / HTTP PATCH

        :param serializer:
        :return:
        """
        logger.info("Handle schedule update request")

        original_funding_source_type = serializer.instance.funding_source_type
        documents = serializer.validated_data.pop("documents", [])
        new_instance = serializer.save()
        serializer.assign_uploaded_documents_to_schedule(documents)

        if self._can_changes_cause_late_payments(original_funding_source_type, new_instance) \
                and not new_instance.have_time_for_nearest_payments_processing_by_scheduler:
            if new_instance.have_time_for_first_payments_processing_manually:
                self._process_first_payments_manually(new_instance)
            else:
                process_late_payments = bool(int(self.request.query_params.get("process_late_payments", 0)))
                if not process_late_payments:
                    raise ConflictError(f'Cannot update schedule. '
                                        f'There are related late payments that should be processed ({new_instance.id})')

                self._process_potential_late_payments(new_instance)

    def _can_changes_cause_late_payments(self, original_funding_source_type, schedule):
        result = original_funding_source_type != schedule.funding_source_type \
               and schedule.funding_source_type != FundingSourceType.WALLET
        logger.info("Can changes cause late payments for schedule (id=%s) result: %s" % (schedule.id, result),
                    extra={'schedule_id': schedule.id})
        return result

    def _process_potential_late_payments(self, schedule):
        logger.info("Processing potential late payments for schedule (id=%s)" % schedule.id,
                    extra={'schedule_id': schedule.id})
        user = self.request.user
        # Make a series of 'failed' payments to keep a chain of payments in order for further overdue processing
        if not schedule.have_time_for_deposit_payment_processing_by_scheduler:
            make_failed_payment.delay(
                user_id=str(user.id),
                payment_account_id=str(user.account.payment_account_id),
                schedule_id=str(schedule.id),
                currency=str(schedule.currency.value),
                payment_amount=int(schedule.deposit_amount),
                additional_information=str(schedule.deposit_additional_information),
                payee_id=str(schedule.payee_id),
                funding_source_id=str(schedule.funding_source_id),
                is_deposit=True
            )

        if not schedule.have_time_for_regular_payment_processing_by_scheduler:
            make_failed_payment.delay(
                user_id=str(user.id),
                payment_account_id=str(user.account.payment_account_id),
                schedule_id=str(schedule.id),
                currency=str(schedule.currency.value),
                payment_amount=int(schedule.payment_amount),
                additional_information=str(schedule.additional_information),
                payee_id=str(schedule.payee_id),
                funding_source_id=str(schedule.funding_source_id),
            )

    def perform_destroy(self, schedule: Schedule):
        """
        Handle HTTP DELETE here.
        We don't remove schedule instance, just changing status and cancelling related payments
        :param schedule:
        :return:
        """

        if not schedule.is_stoppable():
            raise ValidationError({"status": "Schedule with current status cannot be canceled"})

        # stop Schedule
        schedule.move_to_status(ScheduleStatus.stopped)
        self.payment_client.cancel_schedule_payments(schedule.id)

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
        logger.info("Document moved to archive. (Username: %s, Schedule id: %s, Document id: %s.)" % (
            request.user.username, document.schedule.id if document.schedule else None, document.id
        ))
        return Response(None, status=204)

    @transaction.atomic
    @action(methods=['POST'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly | SubUserManageSchedulesPermission,
                    HasParticularSchedulePermission)
            )
    def pay_overdue(self, request, pk=None):
        """
        Tries to initiate the sequence of overdue payments initiated by client.
        :param request:
        :param pk:
        :return:
        """
        schedule_id = pk

        try:
            schedule = Schedule.objects.get(id=schedule_id)
        except Exception as e:
            raise ValidationError("Unable to fetch schedule_id=%s " % schedule_id)

        if not schedule.overdue:
            raise ValidationError("Schedule is expected to be in overdue state")

        if schedule.processing:
            raise ValidationError("Schedule is being processed right now")

        logger.info("Submit make_overdue_payment(schedule_id=%s) task for processing" % schedule_id)
        make_overdue_payment.delay(
            schedule_id=schedule_id,
        )
        return Response(status=status_codes.HTTP_204_NO_CONTENT)

    @transaction.atomic
    @action(methods=['PATCH'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly | SubUserManageSchedulesPermission,
                    HasParticularSchedulePermission)
            )
    def acceptance(self, request, pk=None):
        """
        Used to accept "receive funds" schedule by payer.
        :param request:
        :param pk:
        :return:
        """
        schedule_id = pk

        try:
            schedule = Schedule.objects.get(id=schedule_id)
        except Exception:
            raise NotFound(f'Schedule not found id={schedule_id}')

        serializer = ScheduleAcceptanceSerializer(instance=schedule, data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        payment_fee_amount = serializer.validated_data.get("payment_fee_amount", None)
        deposit_fee_amount = serializer.validated_data.get("deposit_fee_amount", None)
        funding_source_id = serializer.validated_data.get("funding_source_id", None)
        backup_funding_source_id = serializer.validated_data.get("backup_funding_source_id", None)
        funding_source_type = serializer.validated_data.get("funding_source_type", None)
        backup_funding_source_type = serializer.validated_data.get("backup_funding_source_type", None)

        schedule.accept(
            payment_fee_amount, deposit_fee_amount,
            funding_source_id, funding_source_type,
            backup_funding_source_id, backup_funding_source_type
        )

        if not schedule.have_time_for_nearest_payments_processing_by_scheduler:
            if schedule.have_time_for_first_payments_processing_manually:
                self._process_first_payments_manually(schedule)
            else:
                process_late_payments = bool(int(self.request.query_params.get("process_late_payments", 0)))
                if not process_late_payments:
                    raise ConflictError(f'Cannot accept schedule. '
                                        f'There are related late payments that should be processed ({schedule.id})')

                self._process_potential_late_payments(schedule)

        return Response()

    @transaction.atomic
    @action(methods=['PATCH'],
            detail=True,
            permission_classes=(
                    IsAuthenticated, IsActive, IsNotBlocked,
                    IsAccountVerified,
                    IsSuperAdminOrReadOnly | IsOwnerOrReadOnly | SubUserManageSchedulesPermission,
                    HasParticularSchedulePermission)
            )
    def rejection(self, request, pk=None):
        """
        Used to reject "receive funds" schedule by payer.
        :param request:
        :param pk:
        :return:
        """
        schedule_id = pk

        try:
            schedule = Schedule.objects.get(id=schedule_id)
        except Exception:
            raise NotFound(f'Schedule not found {schedule_id}')

        schedule.reject()
        return Response()
