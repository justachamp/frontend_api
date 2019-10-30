from os import environ
import logging

import zeep
from zeep.transports import Transport
from zeep.cache import InMemoryCache
from zeep.wsse.username import UsernameToken
import requests
from requests.auth import HTTPBasicAuth

import core.fields
from core.logger import Timer
from customate.settings import EXTERNAL_SERVICES_TIMEOUT

from external_apis.gbg.settings import GBG_ACCOUNT, GBG_PASSWORD, GBG_WSDL, DEBUG
from external_apis.gbg.models import BankingDetails, PersonalDetails, Address, ContactDetails, IdentityDocument

# Following constants inspired by https://github.com/madmatt/id3global-service
# The const returned by the ID3Global API when this identity passed verification, according to the ruleset used.
BAND_PASS = 'Pass'
# The const returned by the ID3Global API when this identity needs additional referral, according to the ruleset used.
BAND_REFER = 'Refer'
# The const returned by the ID3Global API when this identity needs additional referral, according to the ruleset used.
BAND_ALERT = 'Alert'

zeep_cache = InMemoryCache()
logger = logging.getLogger(__name__)

SERVICE = 'Gbg'


def get_gbg_client():
    """
    Creates WSDL client based on current settings
    :return:
    :rtype: zeep.Client
    """

    token = UsernameToken(GBG_ACCOUNT, GBG_PASSWORD)
    session = requests.Session()
    session.auth = HTTPBasicAuth(GBG_ACCOUNT, GBG_PASSWORD)
    transport = Transport(
        session=session,
        timeout=EXTERNAL_SERVICES_TIMEOUT,
        cache=None if DEBUG else zeep_cache
    )
    return zeep.Client(wsdl=GBG_WSDL, transport=transport, wsse=token)


def get_profile(profile_id, profile_version=None):
    """
    Returns GBG-specific profile info
    :param profile_id:
    :param profile_version:
    :return:
    :rtype: dict
    """
    profile = {
        'ID': profile_id
    }

    if profile_version:
        if "." in profile_version:  # Handle "1.6" cases, which include ProfileRevision
            profile_version, _ = profile_version.split(".")  # current API does not support specifying ProfileRevision
        profile.update({
            'Version': profile_version
        })
    return profile


def validate_banking_details(country: core.fields.Country,
                             banking_details: BankingDetails,
                             personal_details: PersonalDetails,
                             current_address: Address,
                             customer_reference: str):
    """
    Does banking info validation using env-predefined GBG ID3global profile.
    Note: profile_id and validation rulesets must be configured on GBG side.
    :return:
    """
    # Sample payload for bank account verification in UK
    # http://www.id3globalsupport.com/Website/content/Sample%20Code/XML/Text/AuthenticateSP/AuthenticateSP/AuthenticateSP%20UK%20BAV%20FIXED%20FORMAT.txt
    client = get_gbg_client()
    # http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#op.d1e6784
    GlobalAuthenticate_service = client.bind(service_name='ID3global', port_name='basicHttpBinding_GlobalAuthenticate')

    input_data = {
        'Personal': {
            'PersonalDetails': personal_details.gbg_serialization()
        },
        'BankingDetails': banking_details.gbg_serialization(),
        'Addresses': {
            'CurrentAddress': current_address.gbg_serialization()
        }
    }

    logger.info("Request to GBG service for banking details validation (input_data=%r)" % input_data,
                extra={'input_data': input_data, 'service': SERVICE})
    timer = Timer()
    res = GlobalAuthenticate_service.AuthenticateSP(
        ProfileIDVersion=get_profile(
            profile_id=environ["GBG_{}_BANK_VALIDATION_PROFILE_ID".format(country.value)],
            profile_version=environ.get("GBG_{}_BANK_VALIDATION_PROFILE_VERSION".format(country.value), 0)
        ),
        CustomerReference=customer_reference,
        InputData=input_data
    )
    logger.info("Response from GBG for banking details validation (BandText=%s, Score=%s): %r" % (res.BandText, res.Score, res),
                extra={'response': res, 'duration': timer.duration(), 'service': SERVICE})
    return res


def validate_identity_details(country: core.fields.Country,
                              personal_details: PersonalDetails,
                              contact_details: ContactDetails,
                              current_address: Address,
                              identity_document: IdentityDocument,
                              customer_reference: str):
    """
    GBG identity verification.
    Note: profile_id and validation rulesets must be configured on GBG side.
    :return:
    """
    client = get_gbg_client()
    # http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml#op.d1e6784
    GlobalAuthenticate_service = client.bind(service_name='ID3global', port_name='basicHttpBinding_GlobalAuthenticate')

    input_data = {
        'Personal': {
            'PersonalDetails': personal_details.gbg_serialization()
        },
        'Addresses': {
            'CurrentAddress': current_address.gbg_serialization(enable_expanded=True)
        },
        "ContactDetails": contact_details.gbg_serialization(),
    }

    if identity_document:
        input_data.update({
            "IdentityDocuments": identity_document.gbg_serialization()
        })

    logger.info("Request to GBG service for identity details validation (input_data=%r, customer_reference=%r)" % (input_data, customer_reference),
                extra={'input_data': input_data, 'customer_reference': customer_reference, 'service': SERVICE})
    timer = Timer()
    res = GlobalAuthenticate_service.AuthenticateSP(
        ProfileIDVersion=get_profile(
            profile_id=environ["GBG_{}_IDENTITY_VALIDATION_PROFILE_ID".format(country.value)],
            profile_version=environ.get("GBG_{}_IDENTITY_VALIDATION_PROFILE_VERSION".format(country.value), 0)
        ),
        CustomerReference=customer_reference,
        InputData=input_data
    )
    logger.info("Response from GBG for identity details validation (BandText=%s, Score=%s): %r" % (res.BandText, res.Score, res),
                extra={'response': res, 'duration': timer.duration(), 'service': SERVICE})
    return res
