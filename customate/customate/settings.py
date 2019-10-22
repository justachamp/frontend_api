"""
Django settings for customate project.

Generated by 'django-admin startproject' using Django 2.2

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

from os import environ, path
import logging.config
import arrow
from kombu import Queue, Exchange
from celery.schedules import crontab
from corsheaders.defaults import default_headers
from django.utils.log import DEFAULT_LOGGING
from django.core.management.color import supports_color

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = path.dirname(path.dirname(path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'c3rq#fr$u-5d1qsq@qfkyr=he@)9r7)wj1yl_14*bir3z_1hj^'

GENERAL_APP_NAME = 'frontend_api'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = bool(int(environ.get("DEBUG", 0)))

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
    'external_apis.apps.ExternalApisConfig',
    'frontend_api.apps.FrontendApiConfig',
    'payment_api.apps.PaymentApiConfig',
    'storages',
    'django_filters'
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # 'authentication.cognito.middleware.cognito_django_middleware.AwsDjangoMiddleware'
    'customate.middlewares.RequestDetailsLoggingMiddleware',
    'authentication.middlewares.UserActivityMonitoringMiddleware',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

COGNITO_USER_POOL_ID = environ['COGNITO_USER_POOL_ID']
COGNITO_APP_CLIENT_ID = environ['COGNITO_APP_CLIENT_ID']
COGNITO_APP_SECRET_KEY = environ.get('COGNITO_APP_SECRET_KEY')

AWS_ACCESS_KEY = environ['AWS_ACCESS_KEY']
AWS_SECRET_KEY = environ['AWS_SECRET_KEY']

AWS_REGION = environ['AWS_REGION']
AWS_REGION_SES = environ["AWS_REGION_SES"]
AWS_REGION_SNS = environ["AWS_REGION_SNS"]
AWS_SES_NOTIFICATIONS_GOCUSTOMATE_SENDER = environ["AWS_SES_NOTIFICATIONS_GOCUSTOMATE_SENDER"]

COGNITO_ATTR_MAPPING = {
    'email': 'email',
    'given_name': 'first_name',
    'family_name': 'last_name',
    'custom:api_key': 'api_key',
    'custom:api_key_id': 'api_key_id'
}

COGNITO_CREATE_UNKNOWN_USERS = True

# see more at https://lincolnloop.com/blog/django-logging-right-way/
LOGGING_CONFIG = None
LOGLEVEL = environ.get('LOGLEVEL', 'debug' if DEBUG else 'info').upper()
LOGFILEPATH = environ.get('LOGFILEPATH', 'app.log')

logging.config.dictConfig({
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'console': {
            # see more parameters at https://docs.python.org/3/library/logging.html#logging.LogRecord
            'format': '[%(asctime)s %(levelname)s %(pathname)s:%(lineno)s] %(message)s',
            'datefmt': "%y%m%d %H:%M:%S",
        },

        'customate.json.formatter': {
            'class': 'core.logger.CustomateJsonFormatter'
        },

        'colorlog': {
            'class': 'colorlog.ColoredFormatter',
            'format': '%(log_color)s[%(asctime)s %(levelname)s %(pathname)s:%(lineno)s|%(name)s] %(message)s',
            'datefmt': "%y%m%d %H:%M:%S",
        },

        'django.server': {
            '()': 'django.utils.log.ServerFormatter',
            'format': '[{asctime}] {message}',
            'datefmt': "%y%m%d %H:%M:%S",
            'style': '{'
        }
    },
    'handlers': {
        'console': {
            'class': 'colorlog.StreamHandler' if supports_color() else 'logging.StreamHandler',
            'formatter': 'colorlog' if supports_color() else 'console',
        },

        'rotating_file': {
            'class': 'core.logger.BetterRotatingFileHandler',
            'formatter': 'customate.json.formatter',
            'filename': LOGFILEPATH,
            'maxBytes': 1024 * 1024 * 10,  # 10 MB
        },

        'django.server': DEFAULT_LOGGING['handlers']['django.server'],

    },
    'loggers': {
        # "root" logger which serves as a catch-all for any logs that are sent from any Python module
        '': {
            'level': LOGLEVEL,
            'handlers': ['console'],
        },

        'django': {
            'handlers': ['console'],
            'level': 'ERROR',
        },

        'django.request': {
            'handlers': ['console', 'rotating_file'],
            'level': LOGLEVEL,
            'propagate': False,
        },

        # DB queries
        'django.db.backends': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },

        # Logging From Your Application
        'customate': {
            'level': LOGLEVEL,
            'handlers': ['console', 'rotating_file'],
            # required to avoid double logging with root logger
            'propagate': False,
        },

        'authentication': {
            'level': LOGLEVEL,
            'handlers': ['console', 'rotating_file'],
            # required to avoid double logging with root logger
            'propagate': False,
        },

        'external_apis': {
            'level': LOGLEVEL,
            'handlers': ['console', 'rotating_file'],
            # required to avoid double logging with root logger
            'propagate': False,
        },

        'frontend_api': {
            'level': LOGLEVEL,
            'handlers': ['console', 'rotating_file'],
            # required to avoid double logging with root logger
            'propagate': False,
        },

        'payment_api': {
            'level': LOGLEVEL,
            'handlers': ['console', 'rotating_file'],
            # required to avoid double logging with root logger
            'propagate': False,
        },

        # Django-internals logging
        'django.server': DEFAULT_LOGGING['loggers']['django.server'],

        # GBG WSDL client
        'zeep.transports': {
            'level': 'ERROR',
            'propagate': False,
            'handlers': ['console'],
        },

        # Don't log this module at all
        'botocore': {
            'level': 'NOTSET',
            'propagate': False,
        },

        # parso.cache, parso.python.diff
        'parso': {
            'level': 'NOTSET',
            'propagate': False,
        },

        'zeep.xsd': {
            'level': 'NOTSET',
            'propagate': False,
        },
        'zeep.wsdl': {
            'level': 'NOTSET',
            'propagate': False,
        },

    },
})

LOGIN_REDIRECT_URL = '/accounts/profile'

# more settings here https://www.django-rest-framework.org/api-guide/settings/

DEFAULT_RENDERER_CLASSES = (
    'core.renderers.CustomateJSONRenderer',
)

if DEBUG:
    DEFAULT_RENDERER_CLASSES = DEFAULT_RENDERER_CLASSES + (
        'rest_framework.renderers.BrowsableAPIRenderer',
    )


REST_FRAMEWORK = {
    'PAGE_SIZE': 10,
    # need custom handler
    # 'EXCEPTION_HANDLER': 'rest_framework_json_api.exceptions.exception_handler',
    "EXCEPTION_HANDLER": 'customate.utils.exception_handler',

    'DEFAULT_PAGINATION_CLASS': 'rest_framework_json_api.pagination.JsonApiPageNumberPagination',
    'DEFAULT_PARSER_CLASSES': (
        # 'rest_framework_json_api.parsers.JSONParser',
        'core.parsers.JSONAPIBulkParser',
        # 'rest_framework.parsers.FormParser',
        # 'rest_framework.parsers.MultiPartParser'
    ),
    'DEFAULT_RENDERER_CLASSES': DEFAULT_RENDERER_CLASSES,
    'DEFAULT_METADATA_CLASS': 'rest_framework_json_api.metadata.JSONAPIMetadata',
    'DEFAULT_FILTER_BACKENDS': (
        'frontend_api.core.resource.filters.BetterQueryParameterValidationFilter',
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
    'TEST_REQUEST_DEFAULT_FORMAT': 'vnd.api+json',
    'DATE_INPUT_FORMATS': ["%Y-%m-%d"]
}

# DRF JSON_API settings
JSON_API_FORMAT_FIELD_NAMES = False
JSON_API_FORMAT_TYPES = False
JSON_API_PLURALIZE_TYPES = False
JSON_API_UNIFORM_EXCEPTIONS = False

ROOT_URLCONF = 'customate.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [path.join(BASE_DIR, "templates")],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
            'libraries': {
                'prettify_number': 'frontend_api.helpers'
            }
        },
    },
]

WSGI_APPLICATION = 'customate.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': environ['DB_NAME'],
        'HOST': environ['DB_HOST'],
        'PORT': environ['DB_PORT'],
        'USER': environ['DB_USER'],
        'PASSWORD': environ['DB_PASSWORD'],
        'CONN_MAX_AGE': 60 * 10,  # 10 minutes
        'TEST': {
            # this is for ci database creation. if multiple developers
            # trigger tests with a commit we don't want them clobbering each
            # other. we set this value at runtime in the CI environment
            'NAME': environ.get('DB_TEST_NAME', 'test_customate_frontend')
        }
    }
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/
CORS_ORIGIN_ALLOW_ALL = True

CORS_ALLOW_HEADERS = default_headers + (
    'ACCESSTOKEN',
    'IDTOKEN',
    'REFRESHTOKEN'
)

STATIC_ROOT = path.join(BASE_DIR, "static")
AUTH_USER_MODEL = 'core.User'
ALLOWED_HOSTS = ['*']

AWS_ACCESS_KEY_ID = AWS_ACCESS_KEY
AWS_SECRET_ACCESS_KEY = AWS_SECRET_KEY
AWS_DEFAULT_ACL = 'public-read'
AWS_S3_STORAGE_BUCKET_NAME = environ.get('AWS_S3_STORAGE_BUCKET_NAME')
AWS_S3_UPLOAD_DOCUMENTS_PATH = environ.get("AWS_S3_UPLOAD_DOCUMENTS_PATH", "documents")
AWS_S3_CUSTOM_DOMAIN = environ.get('AWS_CDN_HOST')
AWS_S3_OBJECT_PARAMETERS = {
    'CacheControl': 'max-age=86400',
}
AWS_S3_PRESIGNED_URL_EXPIRES_IN = 20  # Expired time in seconds for AWS S3 presigned link
AWS_LOCATION = 'static'
STATIC_URL = 'https://%s/%s/' % (AWS_S3_CUSTOM_DOMAIN, AWS_LOCATION)
STATICFILES_STORAGE = 'storages.backends.s3boto3.S3Boto3Storage'

COUNTRIES_AVAILABLE = environ.get('COUNTRIES_AVAILABLE', '').split(',')
FULL_RESOURCE_LIST_PAGE_SIZE = environ.get('FULL_RESOURCE_LIST_PAGE_SIZE', 200)
PAYMENT_API_URL = environ['PAYMENT_API_URL']

############ CELERY configuration ##################################
CELERY_BROKER_URL = "amqp://{user}:{password}@{host}:{port}/{vhost}".format(
    user=environ['RABBITMQ_USER'],
    password=environ['RABBITMQ_PASSWORD'],
    host=environ.get('RABBITMQ_HOST', "localhost"),
    port=environ.get('RABBITMQ_PORT', 5672),
    vhost=environ.get('RABBITMQ_VHOST', '')
)

# https://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_acks_late
CELERY_TASK_ACKS_LATE = True
# Late ack means that the task messages will be acknowledged after the task has been executed,
# not just before, which is the default behavior.


DEFAULT_EXCHANGE = Exchange('default', type='direct')
# # tasks that require heavy I/O
IO_TASKS = {'queue': 'io_tasks', 'routing_key': 'io_tasks'}
# # lightweight messaging tasks
NOTIFICATION_TASKS = {'queue': 'notification_tasks', 'routing_key': 'notification_tasks'}

CELERY_TASK_DEFAULT_QUEUE = IO_TASKS['queue']
CELERY_TASK_DEFAULT_EXCHANGE = 'default'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = 'direct'

CELERY_TASK_QUEUES = (
    Queue(IO_TASKS['queue'], exchange=DEFAULT_EXCHANGE, routing_key=IO_TASKS['routing_key']),
    Queue(NOTIFICATION_TASKS['queue'], exchange=DEFAULT_EXCHANGE, routing_key=NOTIFICATION_TASKS['routing_key']),
)

# CELERY_TASK_ROUTES = (
#     {'frontend_api.tasks.add': IO_TASKS},
#     {'customate.celery.debug_task': NOTIFICATION_TASKS},
#
# )

CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_BEAT_PER_PAGE_OBJECTS = 5

# This is for periodic execution of tasks
# For more info: http://docs.celeryproject.org/en/latest/userguide/periodic-tasks.html#crontab-schedules
CELERY_BEAT_SCHEDULE = {
     # 'one_per_minute': {
     #    'task': 'frontend_api.tasks.schedules.process_unaccepted_schedules',
     #    'schedule': crontab(minute='*/1'),
     #    'args': ('one_per_hour', False, None)
     # },

    'once_per_day': {
        'task': 'frontend_api.tasks.payments.initiate_daily_payments',
        # Even though bank day is not opened, we initiate payments in the night
        'schedule': crontab(hour='00', minute="01")  # 00:01 UTC every day
    },
    'once_per_day_update_statuses_of_unaccepted_schedules': {
        'task': 'frontend_api.tasks.schedules.process_unaccepted_schedules',
        'schedule': crontab(hour='00', minute="01")  # 00:01 UTC every day
    },
    'once_per_day_remove_unassigned_documents': {
        'task': 'frontend_api.tasks.schedules.remove_unassigned_documents',
        'schedule': crontab(hour='01', minute="00")  # 01:00 UTC every day
    },
}

PAYMENT_SYSTEM_CLOSING_TIME = environ['PAYMENT_SYSTEM_CLOSING_TIME']  # HH:mm format
_ = arrow.get("2000-01-01T%s:00" % PAYMENT_SYSTEM_CLOSING_TIME, ['YYYY-MM-DDTH:mm:ss'])  # make sure we fail early

DOCUMENTS_MAX_LIMIT_PER_SCHEDULE = 5
MAX_ALLOW_USER_INACTIVITY = environ.get('MAX_ALLOW_USER_INACTIVITY', 10)  # in minutes
FIRST_PAYMENTS_MIN_EXECUTION_DELAY = 5  # in seconds
