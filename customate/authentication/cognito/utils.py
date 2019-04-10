import hashlib
import hmac
import base64
import json
import struct
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPublicNumbers
from urllib.request import urlopen
from django.conf import settings

from authentication.cognito.core import constants

import logging
logger = logging.getLogger(__name__)


class PublicKey(object):
    def __init__(self, pubkey):
        self.exponent = self.base64_to_long(pubkey['e'])
        self.modulus = self.base64_to_long(pubkey['n'])
        self.pem = PublicKey.convert(self.exponent, self.modulus)

    def int_array_to_long(self, array):
        return int(''.join(['{:02x}'.format(b) for b in array]), 16)

    def base64_to_long(self, data):
        data = data.encode('ascii')
        _ = base64.urlsafe_b64decode(bytes(data) + b'==')
        return self.int_array_to_long(struct.unpack('%sB' % len(_), _))

    @staticmethod
    def convert(exponent, modulus):
        components = RSAPublicNumbers(exponent, modulus)
        pub = components.public_key(backend=default_backend())
        return pub.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo)


def get_cognito_secret_hash(username: str) -> str:
    sercret_hash = None
    if constants.CLIENT_SECRET:
        logger.error(f'client secret {constants.CLIENT_SECRET}, username: {username}, client id: {constants.CLIENT_ID}')
        message = username + constants.CLIENT_ID
        digest = hmac.new(str(constants.CLIENT_SECRET).encode('UTF-8'), msg=str(message).encode('UTF-8'),
                          digestmod=hashlib.sha256).digest()
        sercret_hash = base64.b64encode(digest).decode()

    return sercret_hash


def get_public_keys():
    public_keys_url = urlopen("https://cognito-idp." + constants.POOL_ID.split("_", 1)[0] + ".amazonaws.com/"
                              + constants.POOL_ID + "/.well-known/jwks.json")
    public_keys = json.loads(public_keys_url.read().decode('utf-8'))

    return public_keys


def cognito_to_dict(attr_list,mapping):
    user_attrs = dict()
    for i in attr_list:
        name = mapping.get(i.get('Name'))
        if name:
            value = i.get('Value')
            user_attrs[name] = value
    return user_attrs


def user_obj_to_django(user_obj):
    c_attrs = settings.COGNITO_ATTR_MAPPING
    user_attrs = dict()
    for k,v in user_obj.__dict__.iteritems():
        dk = c_attrs.get(k)
        if dk:
            user_attrs[dk] = v
    return user_attrs


