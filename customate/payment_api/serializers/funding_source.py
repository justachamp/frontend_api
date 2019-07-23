import logging
from traceback import format_exc
from rest_framework.serializers import ValidationError
from collections import OrderedDict

from external_apis.gbg.models import ContactDetails, PersonalDetails, BankingDetails, Address
from external_apis.gbg.service import validate_banking_details, BAND_PASS

from payment_api.serializers import (
    CharField,
    ResourceMeta,
    JSONField,
    EnumField,
    TypeEnumField,
    Currency,
    FundingSourceType,
    FundingSourceStatus,
    ResourceSerializer,
    ExternalResourceRelatedField
)

logger = logging.getLogger(__name__)


class BaseFundingSourceSerializer(ResourceSerializer):
    title = CharField(required=True)

    class Meta(ResourceMeta):
        resource_name = 'funding_sources'


class FundingSourceSerializer(BaseFundingSourceSerializer):
    included_serializers = {
        'payment_account': 'payment_api.serializers.PaymentAccountSerializer'
    }

    type = TypeEnumField(enum=FundingSourceType, required=True, primitive_value=True)
    status = EnumField(enum=FundingSourceStatus, required=False, primitive_value=True)
    validation_message = CharField(required=False, source='validationMessage')
    currency = EnumField(enum=Currency, required=True, primitive_value=True)
    data = JSONField(required=True)
    address = JSONField(required=False)

    payment_account = ExternalResourceRelatedField(
        required=True,
        related_link_view_name='funding-source-related',
        self_link_view_name='funding-source-relationships',
        source='account'
    )

    class Meta(ResourceMeta):
        #service = 'payment_api.services.FundingSourcesRequestResourceService'
        resource_name = 'funding_sources'

    def direct_debit_gbg_validation(self, res: OrderedDict):
        """
        Validate Direct debit info using GBG banking info validation service.

        :param res: Incoming data
        :type res: OrderedDict
        :return: validated res
        :rtype: OrderedDict
        """
        fs_type = res["type"]
        if fs_type != FundingSourceType.DIRECT_DEBIT.value:
            return res

        logger.debug("GBG direct debit validation on res=%r" % res)
        if res["currency"] != "GBP":
            raise ValidationError({
                "currency": f'{FundingSourceType.DIRECT_DEBIT.label} funding source supports GBP only'
            })

        data = res["data"]
        address = res["address"]
        user = self.get_current_user()
        # first_name, last_name, *_ = data["payer"]["fullName"].split(" ")

        # call gbg service
        gbg_result = validate_banking_details(
            country=user.address.country,
            banking_details=BankingDetails(
                sort_code=data["account"].get("sortCode"),
                account_no=data["account"].get("accountNumber")
            ), personal_details=PersonalDetails(
                first_name=user.first_name,
                last_name=user.last_name,
                middle_name=user.middle_name,
                birth_date=user.birth_date,
                gender=user.gender,
                title=user.title,
                mothers_maiden_name=user.mother_maiden_name,
                country_of_birth=user.country_of_birth
            ), current_address=Address(
                post_code=address["postcode"],
                city=address["city"],
                address_line_1= address.get("address_line_1") or address.get("address"),
                address_line_2=address.get("address_line_2"),
                country=address["country"],
                locality=address["locality"]
            ), contact_details=ContactDetails(
                mobile_phone=str(user.phone_number),
                email=user.email
            ))

        if gbg_result.BandText != BAND_PASS:
            raise ValidationError("GBG validation failed")
        return res

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
        logger.info("VALIDATE, res=%r" % res)
        try:
            res = self.direct_debit_gbg_validation(res)
        except Exception as e:
            logger.error("GBG crash: %r" % format_exc())
            raise ValidationError("GBG validation failed")

        # TODO: add other funding source types validation
        return res

    def create(self, validated_data):
        return super().create(self._remove_new_instance_extra_fields(validated_data))

    # @NOTE: could be generalized: move method to parent and introduce class-member with list of extra fields
    def _remove_new_instance_extra_fields(self, data: dict) -> dict:
        data.pop("address", None)

        return data


class UpdateFundingSourceSerializer(BaseFundingSourceSerializer):
    type = TypeEnumField(enum=FundingSourceType, primitive_value=True, read_only=True)
    currency = EnumField(enum=Currency, primitive_value=True, read_only=True)
    data = JSONField(read_only=True)
