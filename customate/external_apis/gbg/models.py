from enum import Enum
from abc import ABC, abstractmethod
from dataclasses import dataclass
import datetime
from core.fields import Country


def filter_empty_values(res):
    if not isinstance(res, dict):
        return res
    return {k: v for k, v in res.items() if v is not None and v != ''}

class GBGData(ABC):
    @abstractmethod
    def gbg_serialization(self):
        """
        Provide serialization to pass to GBG services
        :return:
        """
        pass


@dataclass(frozen=True)
class PersonalDetails(GBGData):
    first_name: str
    last_name: str

    birth_date: datetime.date = None
    middle_name: str = None
    title: str = None
    gender: str = None

    mothers_maiden_name: str = None
    country_of_birth: str = None

    def gbg_serialization(self):
        """
        More info about GBG fields
        at @link http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#op.d1e6784

        Title - optional, nillable; type string
        Forename - optional, nillable; type string
        MiddleName - optional, nillable; type string
        Surname - optional, nillable; type string
        Gender - optional, nillable; type GlobalGender - type string with restriction - enum { 'Unspecified', 'Unknown', 'Male', 'Female' }
        DOBDay - optional, nillable; type int
        DOBMonth - optional, nillable; type int
        DOBYear - optional, nillable; type int
        Birth - optional, nillable; type GlobalUKBirth
            MothersMaidenName - optional, nillable; type string
            SurnameAtBirth - optional, nillable; type string
            TownOfBirth - optional, nillable; type string
            ProvinceOfBirth - optional, nillable; type string
            MunicipalityOfBirth - optional, nillable; type string
            Country - optional; type GlobalUKBirthsIndexCountry - type string with restriction - enum { 'UNSPECIFIED', 'ENGLANDWALES', 'OTHER' }
        CountryOfBirth - optional, nillable; type string
        SecondSurname - optional, nillable; type string
        AdditionalMiddleNames - optional, nillable; type ArrayOfstring
            string - optional, unbounded, nillable; type string
        :return:
        """
        res = {
            'Title': self.title,
            'Forename': self.first_name,
            'MiddleName': self.middle_name,
            'Surname': self.last_name,
            'Gender': self.gender,
        }

        if self.birth_date:
            res.update({
                'DOBDay': self.birth_date.strftime('%d'),
                'DOBMonth': self.birth_date.strftime('%m'),
                'DOBYear': self.birth_date.strftime('%Y'),
            })
        if self.mothers_maiden_name:
            res.update({
                "Birth": {
                    "MothersMaidenName": self.mothers_maiden_name
                }
            })

        if self.country_of_birth:
            res.update({
                "CountryOfBirth": self.country_of_birth
            })
        # cleanup empty and None fields
        return filter_empty_values(res)


@dataclass(frozen=True)
class Address(GBGData):
    post_code: str
    city: str
    address_line_1: str

    # some defaults
    address_line_2: str = ""
    address_line_3: str = ""
    locality: str = ""
    country: str = "United Kingdom"

    @staticmethod
    def get_full_country_name(cc_name):
        """
        Convert from 2-letter iso country code into full name:
        'DE' => 'Germany',
        'GB' => 'United Kingdom'

        :param cc_name: country name
        :return:
        :rtype: str
        """
        if len(cc_name) == 2 and cc_name.upper() in [e.value for e in Country]:
            return Country[cc_name].label
        return cc_name

    def gbg_serialization(self):
        """
        GBG serialization
        :return:
        """
        res = {
            "Country": Address.get_full_country_name(self.country),
            "Street": "",
            "SubStreet": "",
            "City": self.city,
            "SubCity": "",
            "StateDistrict": self.locality,
            "POBox": "",
            "Region": self.locality,
            "Principality": "",
            "ZipPostcode": self.post_code,
            "DpsZipPlus": "",
            "CedexMailsort": "",
            "Department": "",
            "Company": "",
            "Building": "",
            "SubBuilding": "",
            "Premise": "",
            "AddressLine1": self.address_line_1,
            "AddressLine2": self.address_line_2,
            "AddressLine3": self.address_line_3,
            "AddressLine4": "",
            "AddressLine5": "",
            "AddressLine6": "",
            "AddressLine7": "",
            "AddressLine8": "",
            "FirstYearOfResidence": None,  # int
            "LastYearOfResidence": None,  # int
            "FirstMonthOfResidence": None,  # int
            "LastMonthOfResidence": None  # int
        }

        # cleanup empty and None fields
        return filter_empty_values(res)


@dataclass(frozen=True)
class BankingDetails(GBGData):
    sort_code: str
    account_no: str

    # some defaults
    iban: str = ""

    @staticmethod
    def get_sort_code_and_account_no(iban: str) -> tuple:
        """
        This currently works for GB (United Kingdom) only
        :param iban: IBAN (International Banking Account Number)
        :return: (sort_code, account_no)
        :rtype: tuple
        """
        if not iban.startswith("GB"):
            return None, None

        sort_code = iban[-8 - 6:-8]
        account_no = iban[-8:]
        assert len(account_no) == 8
        assert len(sort_code) == 6

        return sort_code, account_no

    def gbg_serialization(self):
        """
        GBG serialization.

        BankAccount - optional, nillable; type GlobalBankAccount
            SortCode - optional, nillable; type string
            AccountNumber - optional, nillable; type string
        CreditDebitCard - optional, nillable; type GlobalCreditDebitCard
            CardHolderName - optional, nillable; type string
            CardNumber - optional, nillable; type string
            ExpiryMonth - optional, nillable; type int
            ExpiryYear - optional, nillable; type int
            StartMonth - optional, nillable; type int
            StartYear - optional, nillable; type int
            CardIssueNumber - optional, nillable; type string
            CardType - optional, nillable; type GlobalCardType - type string with restriction - enum { 'VISA', 'MASTERCARD', 'DELTA', 'SWITCH', 'AMEX', 'JCB', 'MAESTRO', 'DINERS', 'ELECTRON', 'SOLO', 'CARTEBANCAIRE', 'CARTEBLEUE', 'LASER', 'DISCOVER', 'DANKORT' }
            CardVerificationCode - optional, nillable; type string
            Country - optional, nillable; type string
            State - optional, nillable; type string
            MerchantData - optional, nillable; type string
            ThreeDSecureResponse - optional, nillable; type string

        :return:
        """
        res = {
            "BankAccount": {
                "SortCode": self.sort_code,
                "AccountNumber": self.account_no
            },
            "CreditDebitCard": None
        }

        # cleanup empty and None fields
        return filter_empty_values(res)


@dataclass(frozen=True)
class ContactDetails(GBGData):
    mobile_phone: str
    email: str

    work_phone: str = ""
    land_phone: str = ""

    def gbg_serialization(self):
        """
        GBG serialization.

        LandTelephone - optional, nillable; type GlobalLandTelephone
            ExDirectory - optional, nillable; type boolean
            Number - optional, nillable; type string
        MobileTelephone - optional, nillable; type GlobalMobileTelephone
            Number - optional, nillable; type string
        Email - optional, nillable; type string
        WorkTelephone - optional, nillable; type GlobalWorkTelephone
            Number - optional, nillable; type string
        :return:
        """
        res = {
            "MobileTelephone": {
                "Number": self.mobile_phone
            },
            "Email": self.email
        }

        if self.work_phone:
            res.update({
                "WorkTelephone": {
                    "Number": self.work_phone
                }
            })

        if self.land_phone:
            res.update({
                "LandTelephone": {
                    "Number": self.land_phone
                }
            })

        return {k:filter_empty_values(v) for k,v in res.items()}


class IdentityDocumentType(Enum):
    # see here for source:
    # http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#op.d1e6792
    NewZealand = 1
    InternationalPassport = 2
    EuropeanIdentityCard = 3
    UK = 4
    Australia = 5
    US = 6
    IdentityCard = 7
    Canada = 8
    Mexico = 9
    Brazil = 10
    Spain = 11


class IdentityDocument(GBGData):
    pass


@dataclass(frozen=True)
class UKIdentityDocument(IdentityDocument):
    passport_number: str
    passport_expiry_date: datetime.date

    driving_licence_number: str = ""
    driving_licence_postcode: str = ""

    driving_licence_mailsort: str = ""
    driving_licence_microfiche: str = ""
    driving_licence_issue_number: str = ""
    driving_licence_issue_date: datetime.date = None
    driving_licence_expiry_date: datetime.date = None

    national_insurance_number: str = ""

    doc_type: IdentityDocumentType = IdentityDocumentType.UK

    def gbg_serialization(self):
        """
        GBG serialization.

        Passport - optional, nillable; type GlobalUKPassport
            Number - optional, nillable; type string
            ExpiryDay - optional, nillable; type int
            ExpiryMonth - optional, nillable; type int
            ExpiryYear - optional, nillable; type int
        DrivingLicence - optional, nillable; type GlobalUKDrivingLicence
            Number - optional, nillable; type string
            MailSort - optional, nillable; type string
            Postcode - optional, nillable; type string
            Microfiche - optional, nillable; type string
            IssueDay - optional, nillable; type int
            IssueMonth - optional, nillable; type int
            IssueYear - optional, nillable; type int
            IssueNumber - optional, nillable; type int
            ExpiryDay - optional, nillable; type int
            ExpiryMonth - optional, nillable; type int
            ExpiryYear - optional, nillable; type int
        NationalInsuranceNumber - optional, nillable; type GlobalUKNationalInsuranceNumber
            Number - optional, nillable; type string

        :return:
        """
        res = {
            "Passport": {
                "Number": self.passport_number,
                "ExpiryDay": self.passport_expiry_date.strftime('%d') if self.passport_expiry_date else None,
                "ExpiryMonth": self.passport_expiry_date.strftime('%m') if self.passport_expiry_date else None,
                "ExpiryYear": self.passport_expiry_date.strftime('%Y') if self.passport_expiry_date else None
            }
        }

        if self.driving_licence_number:
            res.update({
                "DrivingLicence": {
                    "Number": self.driving_licence_number,
                    "MailSort": self.driving_licence_mailsort,
                    "Postcode": self.driving_licence_postcode,
                    "Microfiche": self.driving_licence_microfiche,
                    "IssueDay": self.driving_licence_issue_date.strftime('%d')
                    if self.driving_licence_issue_date else None,
                    "IssueMonth": self.driving_licence_issue_date.strftime('%m')
                    if self.driving_licence_issue_date else None,
                    "IssueYear": self.driving_licence_issue_date.strftime('%Y')
                    if self.driving_licence_issue_date else None,
                    "IssueNumber": self.driving_licence_issue_number,
                    "ExpiryDay": self.driving_licence_expiry_date.strftime('%d')
                    if self.driving_licence_expiry_date else None,
                    "ExpiryMonth": self.driving_licence_expiry_date.strftime('%m')
                    if self.driving_licence_expiry_date else None,
                    "ExpiryYear": self.driving_licence_expiry_date.strftime('%Y')
                    if self.driving_licence_expiry_date else None,
                }
            })

        if self.national_insurance_number:
            res.update({
                "NationalInsuranceNumber": {
                    "Number": self.national_insurance_number
                }
            })
        # cleanup empty and None fields
        rr = {k:filter_empty_values(v) for k,v in res.items()}
        return {self.doc_type.name: rr}


@dataclass(frozen=True)
class IdentityCard(IdentityDocument):
    number: str
    country: Country

    doc_type: IdentityDocumentType = IdentityDocumentType.IdentityCard

    def gbg_serialization(self):
        """
        GBG serialization.
          Number - optional, nillable; type string
          Country - optional, nillable; type string
        """
        return {
            self.doc_type.name: {
                "Number": self.number,
                "Country": Address.get_full_country_name(self.country.value)
            }
        }


@dataclass(frozen=True)
class SpainIdentityDocument(IdentityDocument):
    tax_id_number: str
    doc_type: IdentityDocumentType = IdentityDocumentType.Spain

    def gbg_serialization(self):
        """
        GBG serialization.
        Spain - optional, nillable; type GlobalSpain
            TaxIDNumber - optional, nillable; type GlobalSpainTaxIDNumber
            Number - optional, nillable; type string
        """
        return {
            self.doc_type.name: {
                "TaxIDNumber": {
                    "Number": self.tax_id_number
                }
            }
        }
