"""
Django settings for customate project.

Generated by 'django-admin startproject' using Django 2.1.3.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.1/ref/settings/
"""

import os
from corsheaders.defaults import default_headers

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'c3rq#fr$u-5d1qsq@qfkyr=he@)9r7)wj1yl_14*bir3z_1hj^'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core.apps.CoreConfig',
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'polymorphic',
    'phonenumber_field',
    'authentication.apps.AuthenticationConfig',
    'authentication.cognito.apps.CognitoConfig',
    'address.apps.AddressConfig',
    'address.gbg.apps.GbgConfig',
    'address.loqate.apps.LoqateConfig',
    'frontend_api.apps.FrontendApiConfig',
    'payment_api.apps.PaymentApiConfig',
    'storages',
    'guardian',
    'django_filters'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'authentication.cognito.middleware.cognito_django_middleware.AwsDjangoMiddleware'
]

# REST_FRAMEWORK = {
#     'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
#     'PAGE_SIZE': 10
# }

# CACHES = {
#     'default': {
#         'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
#     }
# }

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'guardian.backends.ObjectPermissionBackend'
]
# AUTHENTICATION_BACKENDS = [
#     # 'django.contrib.auth.backends.ModelBackend',
#     # 'authentication.cognito.middleware.cognito_django_authentication.AwsDjangoAuthentication'
# ]

COGNITO_USER_POOL_ID = os.environ.get('COGNITO_USER_POOL_ID')
COGNITO_APP_CLIENT_ID = os.environ.get('COGNITO_APP_CLIENT_ID')
COGNITO_APP_SECRET_KEY = os.environ.get('COGNITO_APP_SECRET_KEY')

AWS_ACCESS_KEY = os.environ.get('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.environ.get('AWS_SECRET_KEY')

AWS_REGION = os.environ.get('AWS_REGION', '')
COGNITO_ATTR_MAPPING = {
        'email': 'email',
        'given_name': 'first_name',
        'family_name': 'last_name',
        'custom:api_key': 'api_key',
        'custom:api_key_id': 'api_key_id'
    }

COGNITO_CREATE_UNKNOWN_USERS = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    # 'filters': {
    #     'require_debug_false': {
    #         '()': 'django.utils.log.RequireDebugFalse',
    #     },
    #     'require_debug_true': {
    #         '()': 'django.utils.log.RequireDebugTrue',
    #     },
    # },
    'formatters': {
        # 'django.server': {
        #     '()': 'django.utils.log.ServerFormatter',
        #     'format': '[%(server_time)s] %(message)s',
        # },
        'console': {
            # exact format is not important, this is the minimum information
            'format': '%(asctime)s %(name)-12s %(levelname)-8s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'console',
        },

        # 'console': {
        #     'level': 'INFO',
        #     'filters': ['require_debug_true'],
        #     'class': 'logging.StreamHandler',
        # },
        # Custom handler which we will use with logger 'django'.
        # We want errors/warnings to be logged when DEBUG=False
        # 'console_on_not_debug': {
        #     'level': 'WARNING',
        #     'filters': ['require_debug_false'],
        #     'class': 'logging.StreamHandler',
        # },
        # 'django.server': {
        #     'level': 'INFO',
        #     'class': 'logging.StreamHandler',
        #     'formatter': 'django.server',
        # },
        # 'mail_admins': {
        #     'level': 'ERROR',
        #     'filters': ['require_debug_false'],
        #     'class': 'django.utils.log.AdminEmailHandler'
        # }
    },
    'loggers': {
        'django': {
            'handlers': ['console',
                         # 'mail_admins', 'console_on_not_debug'
            ]
            ,
            'level': 'INFO',
        },
        # 'django.request': {
        #     'handlers': ['console'],
        #     'level': 'INFO',
        #     'propagate': True,
        # },


        # 'django.server': {
        #     'handlers': ['django.server'],
        #     'level': 'INFO',
        #     'propagate': False,
        # },
    }
}



LOGIN_REDIRECT_URL = '/accounts/profile'

REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    'EXCEPTION_HANDLER': 'rest_framework_json_api.exceptions.exception_handler',
    'DEFAULT_PAGINATION_CLASS':
        'rest_framework_json_api.pagination.JsonApiPageNumberPagination',
    'DEFAULT_PARSER_CLASSES': (
        # 'rest_framework_json_api.parsers.JSONParser',
        'core.parsers.JSONAPIBulkParser',
        # 'rest_framework.parsers.FormParser',
        # 'rest_framework.parsers.MultiPartParser'
    ),
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
        # 'core.renderers.JSONRenderer',
        # If you're performance testing, you will want to use the browseable API
        # without forms, as the forms can generate their own queries.
        # If performance testing, enable:
        # 'example.utils.BrowsableAPIRendererWithoutForms',
        # Otherwise, to play around with the browseable API, enable:
        'rest_framework.renderers.BrowsableAPIRenderer'
    ),
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
    'DEFAULT_FILTER_BACKENDS': (
        'rest_framework_json_api.filters.QueryParameterValidationFilter',
        'rest_framework_json_api.filters.OrderingFilter',
        'rest_framework_json_api.django_filters.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
    ),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'authentication.cognito.middleware.cognito_rest_authentication.AwsRestAuthentication',
    ),
    'ORDERING_PARAM': 'sort',


    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),

    # 'DEFAULT_THROTTLE_CLASSES': (
    #     'rest_framework.throttling.AnonRateThrottle',
    #     'rest_framework.throttling.UserRateThrottle'
    # ),
    # 'DEFAULT_THROTTLE_RATES': {
    #     'anon': '100/sec',
    #     'user': '100/sec'
    # },
    'SEARCH_PARAM': 'filter[search]',
    'TEST_REQUEST_RENDERER_CLASSES': (
        'rest_framework_json_api.renderers.JSONRenderer',
    ),
    'TEST_REQUEST_DEFAULT_FORMAT': 'vnd.api+json'
}


REST_PROXY = {
    'HOST': 'https://dev-api.gocustomate.com',
    'AUTH': {
        'user': None,
        'password': None,
        'token': None,
    },
    'TIMEOUT': None,
    'DEFAULT_HTTP_ACCEPT': 'application/vnd.api+json',
    'DEFAULT_HTTP_ACCEPT_LANGUAGE': 'en-US,en;q=0.8',
    'DEFAULT_CONTENT_TYPE': 'application/vnd.api+json',

    # Return response as-is if enabled
    'RETURN_RAW': False,

    # Used to translate Accept HTTP field
    'ACCEPT_MAPS': {
        'text/html': 'application/vnd.api+json',
    },

}


ROOT_URLCONF = 'customate.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'customate.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        # 'NAME': 'customate_frontend',
        # 'USER': 'customate',
        # 'PASSWORD': 'customate',
        # 'HOST': 'postgres',
        # 'PORT': 5432,

        'NAME': os.environ.get('DB_NAME'),
        'HOST': os.environ.get('DB_HOST'),
        'PORT': os.environ.get('DB_PORT'),
        'USER': os.environ.get('DB_USER'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'CONN_MAX_AGE': 60 * 10,  # 10 minutes
        'TEST':  {
            # this is for ci database creation. if multiple developers
            # trigger tests with a commit we don't want them clobbering each
            # other. we set this value at runtime in the CI environment
            'NAME': os.environ.get('DB_TEST_NAME', 'test_customate_frontend')
        }
    }
}



# Password validation
# https://docs.djangoproject.com/en/2.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.1/howto/static-files/
CORS_ORIGIN_ALLOW_ALL = True
# GUARDIAN_GET_CONTENT_TYPE = 'polymorphic.contrib.guardian.get_polymorphic_base_content_type'

CORS_ALLOW_HEADERS = default_headers + (
    'ACCESSTOKEN',
    'IDTOKEN',
    'REFRESHTOKEN'
)


STATIC_ROOT = os.path.join(BASE_DIR, "static")
AUTH_USER_MODEL = 'core.User'
ALLOWED_HOSTS = ['*']

AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = AWS_SECRET_KEY
AWS_DEFAULT_ACL = 'public-read'
AWS_STORAGE_BUCKET_NAME = os.getenv('AWS_S3_STORAGE_BUCKET_NAME')
AWS_S3_CUSTOM_DOMAIN = os.getenv('AWS_CDN_HOST')
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_LOCATION = 'static'
STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

COUNTRIES_AVAILABLE = os.environ.get('COUNTRIES_AVAILABLE', '').split(',')




