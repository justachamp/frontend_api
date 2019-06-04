from os import environ

'''
    We're using a number of GBG services to do data validation:
      * Loqate -- to do address lookups
      * ID3Global  -- to validate identities, bank accounts, personal details, phones, etc.
      
    ID3global API integration and code samples:
     https://www.id3globalsupport.com/resources/#SampleCode
     http://www.id3globalsupport.com/Website/content/Sample%20Code/Web%20Dev%20Guide%20HTML/html/7a1f23ea-457c-4b05-861d-7d500b5b5133.htm
    
    ID3global test data:
     https://www.id3globalsupport.com/test-data/  
     
    ID3global WSDL inspection:
    http://www.id3globalsupport.com/Website/content/Web-Service/WSDL%20Page/WSDL%20HTML/ID3%20Global%20WSDL-%20Live.xhtml
    
    Service status:
      https://www.gbgstatus.com/
      
      
    Quickly inspect WSDL endpoint:
    python -m zeep "https://pilot.id3global.com/ID3gWS/ID3global.svc?wsdl"
    
'''

DEBUG = environ['DEBUG']

GBG_ACCOUNT = environ['GBG_ACCOUNT']
GBG_PASSWORD = environ['GBG_PASSWORD']
GBG_WSDL = environ.get('GBG_WSDL', "https://pilot.id3global.com/ID3gWS/ID3global.svc?wsdl" if DEBUG
                       else "https://id3global.com/ID3gWS/ID3global.svc?wsdl")


# read list of available countries in Alpha-2 codes (ISO 3166 international standard)
COUNTRIES_AVAILABLE = environ.get('COUNTRIES_AVAILABLE', '').split(',')

# check that corresponding GBG profiles exist for every country defined above
for c in COUNTRIES_AVAILABLE:
    _ = environ["GBG_{}_BANK_VALIDATION_PROFILE_ID".format(c)]
    _ = environ["GBG_{}_IDENTITY_VALIDATION_PROFILE_ID".format(c)]
