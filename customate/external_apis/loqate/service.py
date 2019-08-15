import copy
import requests
import logging
from typing import List, Dict

from external_apis.loqate.settings import LOQATE_SERVICE_KEY
from customate.settings import COUNTRIES_AVAILABLE

BASE_URL = 'https://api.addressy.com/Capture/Interactive/{0}/v1.00/json3ex.ws'
BASE_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'CountryCode': 'GB'
}

logger = logging.getLogger(__name__)


class LoqateError(Exception):
    """
    Custom exception for Loqate service error responses
    """

    def __init__(self, message, error_response):
        # Call the base class constructor with the parameters it needs
        super().__init__(message)
        self.error_response = error_response

    def __str__(self):
        return "LoqateError: %s %s" % (
            self.error_response.get("Cause"),
            self.error_response.get("Resolution")
        )


def make_request(url, params):
    new_params = copy.deepcopy(params)
    # include service key in each request
    new_params.update({"Key": LOQATE_SERVICE_KEY})

    if "Countries" not in new_params:
        if "country" in new_params:
            new_params.update({
                "Countries": new_params['country']
            })
        else:
            new_params.update({
                "Countries": ','.join(COUNTRIES_AVAILABLE)
            })

    # lowercase ids -> uppercase ids
    id = new_params.pop('id', None)
    if id:
        new_params["Id"] = id
    return requests.post(url, headers=BASE_HEADERS, params=new_params)


def _check_errors(items: List):
    """
    Raises custom Loqate exception in case any errors in response.
    This is how an error looks like:
    ```
    [{
       "Error":"1001",
       "Description":"Id Invalid",
       "Cause":"The Id parameter supplied was invalid.",
       "Resolution":"You should only pass in IDs that have been returned from the Find service."
    }]
    ```
    :param items:
    :return:
    """
    if len(items) == 0:
        return

    item = items[0]
    if "Error" in item.keys():
        raise LoqateError(message=item.get("Cause"), error_response=item)


def find_address(params: Dict) -> List:
    """
    Suggest an address given params.
    Sample response:
    ```
        [
         {'Id': 'GB|RM|B|20263145',
          'Type': 'Address',
          'Text': 'Furtherhouse, Highbrook, Hammingden Lane',
          'Highlight': '0-12',
          'Description': 'Ardingly, Haywards Heath, RH17 6SS'
          },
         {'Id': 'GB|RM|ENG|PRESTON-FRECKLETON--ROAD-FURTHER_ENDS',
          'Type': 'Street',
          'Text': 'Further Ends Road',
          'Highlight': '0-7',
          'Description': 'Freckleton, Preston, PR4 1RL - 16 Addresses'
          }
        ]
    ```
    :param params:
    :return:
    :rtype
    """
    r = make_request(url=BASE_URL.format("Find"), params=params)
    items = r.json().get('Items')
    _check_errors(items)
    return items


def retrieve_address(params):
    """
    Retrieve an address given params.
    Sample response:
    ```
      [{
        "id": "GB|RM|B|1454411",
        "domestic_id": "1454411",
        "language": "ENG",
        "language_alternatives": "ENG",
        "department": "",
        "company": "",
        "sub_building": "",
        "building_number": "",
        "building_name": "Further Clough Head Cottage",
        "secondary_street": "",
        "street": "Further Clough Head",
        "block": "",
        "neighbourhood": "",
        "district": "",
        "city": "Nelson",
        "line1": "Further Clough Head Cottage",
        "line2": "Further Clough Head",
        "line3": "",
        "line4": "",
        "line5": "",
        "admin_area_name": "Lancashire",
        "admin_area_code": "",
        "province": "Lancashire",
        "province_name": "Lancashire",
        "province_code": "",
        "postal_code": "BB9 0LH",
        "country_name": "United Kingdom",
        "country_iso2": "GB",
        "country_iso3": "GBR",
        "country_iso_number": 826,
        "sorting_number1": "25233",
        "sorting_number2": "",
        "barcode": "(BB90LH1BS)",
        "po_box_number": "",
        "label": "Further Clough Head Cottage\nFurther Clough Head\nNELSON\nBB9 0LH\nUNITED KINGDOM",
        "type": "Residential",
        "data_level": "Premise",
        "field1": "",
        "field2": "",
        "field3": "",
        "field4": "",
        "field5": "",
        "field6": "",
        "field7": "",
        "field8": "",
        "field9": "",
        "field10": "",
        "field11": "",
        "field12": "",
        "field13": "",
        "field14": "",
        "field15": "",
        "field16": "",
        "field17": "",
        "field18": "",
        "field19": "",
        "field20": ""
     }]
    ```
    :param params:
    :return:
    """
    r = make_request(url=BASE_URL.format("Retrieve"), params=params)
    items = r.json().get('Items')
    _check_errors(items)
    return items
