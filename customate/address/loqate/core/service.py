import requests
from address import settings


class Address:
    _provider = None
    _base_url = 'https://api.addressy.com/Capture/Interactive/{0}/v1.00/json3ex.ws'
    _headers = {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'CountryCode': 'GB'
    }

    def __init__(self):
        self._key = getattr(settings, 'LOQATE_SERVICE_KEY')
        self._provider = requests

    @property
    def headers(self):
        return self._headers

    @property
    def provider(self):
        return self._provider

    def _request(self, url, params):
        params.update({'Key': self._key})

        r = self._provider.post(url, headers=self.headers, params=params)
        try:
            data = r.json()
            print('json data', data)
            items = data.get('Items')
            if items and len(items) and items[0].get('Error', False):
                raise Exception(items[0].get('Description'))
            return items
        except Exception as e:
            print('ex', r.text)
            raise e

    def find(self, params):
        url = self._base_url.format('Find')
        return self._request(url, params)

    def retrieve(self, params):
        url = self._base_url.format('Retrieve')
        return self._request(url, params)



