import logging
from datetime import datetime

from django.utils.functional import cached_property
from rest_framework.exceptions import ValidationError
from traceback import format_exc

from customate import settings
from frontend_api.models import PayeeDetails, FundingSourceDetails, PaymentDetails
from payment_api.core.client import Client
from payment_api.serializers import PaymentAccountSerializer
from payment_api.serializers.payment import ForcePaymentSerializer, MakePaymentSerializer
from payment_api.services.payee import PayeeRequestResourceService
from payment_api.services.source import FundingSourceRequestResourceService

logger = logging.getLogger(__name__)


class PaymentApiClient:
    """
    TODO: rewrite this crappy client to use explicit JSON REST API calls to Payment-api backend.
    Get rid of:
      * Views
      * Serializers
      * Services
      * ANY dependency on payment-api package

    """
    _base_url = settings.PAYMENT_API_URL

    def __init__(self, user):
        self._user = user

    @cached_property
    def client(self):
        return Client(self._base_url)

    def assign_payment_account(self):
        user = self._user
        payment_account_id = None
        if user and user.is_owner and user.contact_verified and not user.account.payment_account_id:
            from payment_api.views import PaymentAccountViewSet
            view = PaymentAccountViewSet()
            serializer = PaymentAccountSerializer(
                data={
                    'email': user.email,
                    'full_name': user.get_full_name() or user.email,
                    'original_account_id': user.account.id
                },
                context={'view': view}
            )
            serializer.is_valid(True)
            data = serializer.save()
            payment_account_id = data.id
            user.account.payment_account_id = payment_account_id
            user.account.save()
        return payment_account_id

    def assign_payment_service_account(self, service_account_type):
        user = self._user

        if user and user.is_owner and not user.account.payment_account_id:
            from payment_api.views import PaymentAccountViewSet
            view = PaymentAccountViewSet()
            view.Meta.resource_suffix_name = service_account_type

            serializer = PaymentAccountSerializer(
                data={
                    'email': user.email,
                    'full_name': user.get_full_name() or user.email,
                    'original_account_id': user.account.id
                },
                context={'view': view}
            )
            serializer.is_valid(True)
            data = serializer.save()
            payment_account_id = data.id
            user.account.payment_account_id = payment_account_id
            user.account.save()
        else:
            raise ValidationError('Specified user is not account owner or already has related payment account')

        return payment_account_id

    def deactivate_account(self, account_id):
        try:
            logger.info("Deactivating account=%s" % account_id)
            self.client.delete('accounts', account_id)
        except Exception as e:
            logger.error("Account deactivation thrown an exception: %r" % format_exc())
            raise e

    def cancel_schedule_payments(self, schedule_id):
        #TODO: replace by call to new client
        try:
            logger.info("Cancelling payments for schedule_id=%r" % schedule_id)
            self.client.delete('schedule_payments', schedule_id)
        except Exception as e:
            logger.error("Schedule payments cancellation thrown an exception: %r" % format_exc())
            raise e


    @staticmethod
    def create_payment(p: PaymentDetails):
        """
        TODO: Refactor this crappy Payment API call and make sure we return explicit DataClass-alike return type
        TODO: and NOT `PaymentResource`! See .get_funding_source_details() for instance
        :param p:
        :return:
        """
        from payment_api.views.payment import MakePaymentViewSet
        logger.info("Creating payment from payment details=%r" % p)

        view = MakePaymentViewSet()
        serializer = MakePaymentSerializer(
            data={
                'id': str(p.id),
                'user_id': str(p.user_id),
                'schedule_id': str(p.schedule_id),
                'currency': p.currency.name,
                'data': {
                    'amount': p.amount,
                    'description': p.description,
                    'parentPaymentId': str(p.parent_payment_id) if p.parent_payment_id else None,
                    'executionDate': datetime.timestamp(p.execution_date) if p.execution_date else None
                },
                'payment_account': {'id': str(p.payment_account_id), 'type': 'payment_accounts'},
                'origin': {'id': str(p.funding_source_id), 'type': 'funding_sources'},
                'recipient': {'id': str(p.payee_id), 'type': 'payees'}
            },
            context={'view': view}
        )
        serializer.is_valid(True)
        return serializer.save()

    def get_payee_details(self, payee_id) -> PayeeDetails:
        try:
            logger.info("Getting payee details (id=%r)" % payee_id)
            service = PayeeRequestResourceService(resource=self)
            resource = service.get_payee_details(payee_id)

            return PayeeDetails(
                id=resource.id,
                title=resource.title,
                type=resource.attributes.type,  # @NOTE ResourceObject has its own "type" field
                iban=resource['data']['account']['iban'],
                recipient_name=resource['data']['recipient']['fullName'],
                recipient_email=resource['data']['recipient']['email'],
                payment_account_id=resource.account.id
            )
        except KeyError as e:
            logger.error("Key error occurred during payee (id=%r) processing (mapping changed?): %r" % (
                payee_id, format_exc()
            ))
            raise e
        except Exception as e:
            logger.error("Receiving payee details (id=%r) thrown an exception: %r" % (
                payee_id, format_exc()
            ))
            raise e

    def get_funding_source_details(self, source_id) -> FundingSourceDetails:
        try:
            logger.info("Getting funding source details (id=%r)" % source_id)
            service = FundingSourceRequestResourceService(resource=self)
            resource = service.get_source_details(source_id)

            return FundingSourceDetails(
                id=resource.id,
                type=resource.attributes.type,  # @NOTE ResourceObject has its own "type" field
                currency=resource.currency,
                payment_account_id=resource.account.id
            )
        except KeyError as e:
            logger.error("Key error occurred during funding source (id=%r) processing (mapping changed?): %r" % (
                source_id, format_exc()
            ))
            raise e
        except Exception as e:
            logger.error("Receiving funding source details (id=%r) thrown an exception: %r" % (
                source_id, format_exc()
            ))
            raise e
