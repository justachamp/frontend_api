from os import environ

LOQATE_SERVICE_KEY = environ['LOQATE_SERVICE_KEY']

GBG_ACCOUNT = environ['GBG_ACCOUNT']
GBG_PASSWORD = environ['GBG_PASSWORD']
GBG_WDSL = environ['GBG_WDSL']

GBG_GB_PROFILE_ID = environ.get('GBG_GB_PROFILE_ID', None)
GBG_IE_PROFILE_ID = environ.get('GBG_IE_PROFILE_ID', None)
GBG_DE_PROFILE_ID = environ.get('GBG_DE_PROFILE_ID', None)
GBG_IT_PROFILE_ID = environ.get('GBG_IT_PROFILE_ID', None)
GBG_NL_PROFILE_ID = environ.get('GBG_NL_PROFILE_ID', None)
GBG_FR_PROFILE_ID = environ.get('GBG_FR_PROFILE_ID', None)
GBG_ES_PROFILE_ID = environ.get('GBG_ES_PROFILE_ID', None)
GBG_PT_PROFILE_ID = environ.get('GBG_PT_PROFILE_ID', None)

GBG_PROFILE_VERSION = environ.get('GBG_PROFILE_VERSION')