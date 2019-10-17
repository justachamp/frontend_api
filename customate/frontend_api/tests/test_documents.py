import os
from unittest import skip
from django.test import SimpleTestCase
from django.conf import settings

import requests
import boto3
from botocore.config import Config


@skip("rewrite without actual requests to AWS")
class TestS3Storage(SimpleTestCase):
    """
    Test correct posting to S3 storage.
    Methods runs in order:
        1. test_a_post_file_to_s3
        2. test_b_get_file_from_s3
        3. test_c_delete_file_from_s3
    """

    def setUp(self):
        self.client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY,
                                   aws_secret_access_key=settings.AWS_SECRET_KEY,
                                   region_name=settings.AWS_REGION,
                                   config=Config(signature_version="s3v4"))
        self.filename = "test_s3_file.pdf"

    @property
    def filepath(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), self.filename)

    def test_a_get_presigned_url_via_boto3_and_post_file_to_s3_with_given_url(self):
        response = self.client.generate_presigned_post(settings.AWS_STORAGE_BUCKET_NAME,
                                                       self.filename,
                                                       ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRES_IN)
        with open(self.filepath, 'rb') as f:
            files = {'file': (self.filename, f)}
            http_response = requests.post(response['url'], data=response['fields'], files=files)
        self.assertEqual(http_response.status_code, 204)

    def test_b_receive_presigned_url_via_boto3_and_get_file_from_s3_by_given_url(self):
        url = self.client.generate_presigned_url('get_object',
                                                 Params={
                                                     'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                                                     'Key': self.filename},
                                                 ExpiresIn=settings.AWS_S3_PRESIGNED_URL_EXPIRES_IN)
        response = requests.get(url)
        self.assertEqual(response.status_code, 200)
