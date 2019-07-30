import copy
import requests
from typing import List, Dict

from external_apis.loqate.settings import LOQATE_SERVICE_KEY
from customate.settings import COUNTRIES_AVAILABLE

BASE_URL = 'https://api.addressy.com/Capture/Interactive/{0}/v1.00/json3ex.ws'
BASE_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'CountryCode': 'GB'
}


def make_request(url, params):
    new_params = copy.deepcopy(params)
    # include service key in each request
    new_params.update({"Key": LOQATE_SERVICE_KEY})
    if "Countries" not in new_params:
        new_params.update({
            "Countries": ','.join(COUNTRIES_AVAILABLE)
        })
    # some unknown magic??
    id = new_params.pop('id', None)
    if id:
        new_params["Container"] = id
    return requests.post(url, headers=BASE_HEADERS, params=new_params)


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
    return r.json().get('Items')


def retrieve_address(params):
    """
    Retrieve an address given params
    :param params:
    :return:
    """
    r = make_request(url=BASE_URL.format("Retrieve"), params=params)
    return r.json().get('Items')
