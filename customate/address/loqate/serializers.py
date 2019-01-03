from rest_framework_json_api import serializers
from address.loqate.models import RetrieveAddress
from address.loqate.core.service import Address as SearchAddressService
import logging
logger = logging.getLogger(__name__)


class SearchAddressSerializer(serializers.Serializer):
    Id = serializers.CharField(max_length=250, required=False, source='id', allow_blank=True, allow_null=True)
    Type = serializers.CharField(max_length=200, source='type', required=False, allow_blank=True)
    Text = serializers.CharField(max_length=250, source='text', required=False, allow_blank=True)
    Highlight = serializers.CharField(max_length=100, source='highlight', required=False, allow_blank=True)
    Description = serializers.CharField(max_length=250, source='description', required=False, allow_blank=True)
    Origin = serializers.CharField(max_length=100, source='origin', required=False, allow_blank=True)
    Countries = serializers.CharField(max_length=100, source='countries', required=False, allow_blank=True)
    Limit = serializers.IntegerField(max_value=100, min_value=1, required=False, source='limit')
    Language = serializers.CharField(max_length=100, source='language', required=False, allow_blank=True)

    def find(self, data):

        service = SearchAddressService()
        # countries = data.get('countries', 'EU')

        params = {
            "Text": data.get('text'),
            # "Origin": data.get('origin', countries),
            # "Countries": countries,
            "Limit": data.get('limit', 10),
            "Language": data.get('language', ''),
        }

        if data.get('id'):
            params['Container'] = data.get('id')


        data = service.find(params)
        logger.error(f'retrieve validated_data {data}')

        serializer = SearchAddressSerializer(data=data,  many=True)
        if serializer.is_valid(True):
            return serializer.validated_data


class RetrieveAddressSerializer(serializers.Serializer):
    Id = serializers.CharField(max_length=200, required=True, source='id')
    DomesticId = serializers.CharField(max_length=200, source='domestic_id', required=False, allow_blank=True)
    Language = serializers.CharField(max_length=100, required=False, source='language', allow_blank=True)
    LanguageAlternatives = serializers.CharField(max_length=100, source='language_alternatives', required=False, allow_blank=True)
    Department = serializers.CharField(max_length=200, source='department', required=False, allow_blank=True)
    Company = serializers.CharField(max_length=200, source='company', required=False, allow_blank=True)
    SubBuilding = serializers.CharField(max_length=100, source='sub_building', required=False, allow_blank=True)
    BuildingNumber = serializers.CharField(max_length=100, source='building_number', required=False, allow_blank=True)
    BuildingName = serializers.CharField(max_length=100, source='building_name', required=False, allow_blank=True)
    SecondaryStreet = serializers.CharField(max_length=200, source='secondary_street', required=False, allow_blank=True)
    Block = serializers.CharField(max_length=200, source='block', required=False, allow_blank=True)
    Neighbourhood = serializers.CharField(max_length=200, source='neighbourhood', required=False, allow_blank=True)
    District = serializers.CharField(max_length=200, source='district', required=False, allow_blank=True)
    City = serializers.CharField(max_length=100, source='city', required=False, allow_blank=True)
    Line1 = serializers.CharField(max_length=100, source='line1', required=False, allow_blank=True)
    Line2 = serializers.CharField(max_length=100, source='line2', required=False, allow_blank=True)
    Line3 = serializers.CharField(max_length=100, source='line3', required=False, allow_blank=True)
    Line4 = serializers.CharField(max_length=100, source='line4', required=False, allow_blank=True)
    Line5 = serializers.CharField(max_length=100, source='line5', required=False, allow_blank=True)
    AdminAreaName = serializers.CharField(max_length=200, source='admin_area_name', required=False, allow_blank=True)
    AdminAreaCode = serializers.CharField(max_length=200, source='admin_area_code', required=False, allow_blank=True)
    Province = serializers.CharField(max_length=200, source='province', required=False, allow_blank=True)
    ProvinceName = serializers.CharField(max_length=200, source='province_name', required=False, allow_blank=True)
    ProvinceCode = serializers.CharField(max_length=100, source='province_code', required=False, allow_blank=True)
    PostalCode = serializers.CharField(max_length=100, source='postal_code', required=False, allow_blank=True)
    CountryName = serializers.CharField(max_length=100, source='country_name', required=False, allow_blank=True)
    CountryIso2 = serializers.CharField(max_length=2, source='country_iso_2', required=False, allow_blank=True)
    CountryIso3 = serializers.CharField(max_length=3, source='country_iso_3', required=False, allow_blank=True)
    CountryIsoNumber = serializers.IntegerField(source='country_iso_number', required=False)
    SortingNumber1 = serializers.CharField(max_length=100, source='sorting_number_1', required=False, allow_blank=True)
    SortingNumber2 = serializers.CharField(max_length=100, source='sorting_number_2', required=False, allow_blank=True)
    Barcode = serializers.CharField(max_length=100, source='barcode', required=False, allow_blank=True)
    POBoxNumber = serializers.CharField(max_length=100, source='po_box_number', required=False, allow_blank=True)
    Label = serializers.CharField(max_length=250, source='label', required=False, allow_blank=True)
    Field1 = serializers.CharField(max_length=250, source='field1', required=False, allow_blank=True)
    Field2 = serializers.CharField(max_length=250, source='field2', required=False, allow_blank=True)
    Field3 = serializers.CharField(max_length=250, source='field3', required=False, allow_blank=True)
    Field4 = serializers.CharField(max_length=250, source='field4', required=False, allow_blank=True)
    Field5 = serializers.CharField(max_length=250, source='field5', required=False, allow_blank=True)
    Field6 = serializers.CharField(max_length=250, source='field6', required=False, allow_blank=True)
    Field7 = serializers.CharField(max_length=250, source='field7', required=False, allow_blank=True)
    Field8 = serializers.CharField(max_length=250, source='field8', required=False, allow_blank=True)
    Field9 = serializers.CharField(max_length=250, source='field9', required=False, allow_blank=True)
    Field10 = serializers.CharField(max_length=250, source='field10', required=False, allow_blank=True)
    Field11 = serializers.CharField(max_length=250, source='field11', required=False, allow_blank=True)
    Field12 = serializers.CharField(max_length=250, source='field12', required=False, allow_blank=True)
    Field13 = serializers.CharField(max_length=250, source='field13', required=False, allow_blank=True)
    Field14 = serializers.CharField(max_length=250, source='field14', required=False, allow_blank=True)
    Field15 = serializers.CharField(max_length=250, source='field15', required=False, allow_blank=True)

    def retrieve(self, id):

        service = SearchAddressService()

        data = service.retrieve({'id': id})
        logger.error(f'retrieve validated_data {data}')

        serializer = RetrieveAddressSerializer(data=data,  many=True)
        if serializer.is_valid(True):
            return serializer.validated_data
