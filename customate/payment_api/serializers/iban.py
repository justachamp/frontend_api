from payment_api.serializers import (
    IbanField,
    CharField,
    EnumField,
    ResourceMeta,
    ResourceSerializer,
    Serializer,
    Country,

)

from core.fields import SerializerField


class BankAddressSerializer(Serializer):
    postcode = CharField(required=True)
    city = CharField(required=True)
    address_line_1 = CharField(required=True)
    address_line_2 = CharField(required=True)
    country = EnumField(enum=Country, required=True, primitive_value=True)


class BankInfoSerializer(Serializer):
    name = CharField(required=True)
    address = BankAddressSerializer(required=True)


class AccountInfoSerializer(Serializer):
    bic = CharField(required=True)
    account_number = CharField(required=True, source='accountNumber')


class IbanValidationSerializer(ResourceSerializer):
    iban = IbanField(required=True)
    bank = SerializerField(resource=BankInfoSerializer, read_only=True)
    account = SerializerField(resource=AccountInfoSerializer, read_only=True)

    class Meta(ResourceMeta):
        resource_name = 'ibans'


class SortCodeAccountNumberValidationSerializer(ResourceSerializer):
    country = EnumField(enum=Country, required=True, primitive_value=True)
    sort_code = CharField(required=True, source='bankCode')
    account_number = CharField(required=True, source='accountNumber')
    branch = CharField(required=False, allow_blank=True)
    bank = SerializerField(resource=BankInfoSerializer, read_only=True)
    account = SerializerField(resource=AccountInfoSerializer, read_only=True)

    class Meta(ResourceMeta):
        resource_name = 'ibans'


class CheckGBSerializer(ResourceSerializer):
    country = EnumField(enum=Country, required=True, primitive_value=True)

    @staticmethod
    def validate_country(country_code):
        return country_code if country_code == Country.GB.value else False


