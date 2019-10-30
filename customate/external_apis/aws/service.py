import logging
import boto3
from botocore.config import Config
from customate import settings
from customate.settings import EXTERNAL_SERVICES_TIMEOUT

logger = logging.getLogger(__name__)


def get_aws_client(service_name, region_name=settings.AWS_REGION, *args, **kwargs):
    return boto3.client(service_name,
                        region_name=region_name,
                        aws_access_key_id=settings.AWS_ACCESS_KEY,
                        aws_secret_access_key=settings.AWS_SECRET_KEY,
                        config=Config(connect_timeout=EXTERNAL_SERVICES_TIMEOUT, read_timeout=EXTERNAL_SERVICES_TIMEOUT,
                                      retries={'max_attempts': 1}, signature_version="s3v4"),
                        *args, **kwargs)
