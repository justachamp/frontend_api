from django.test import TestCase, Client
from frontend_api.models import Document, Schedule


class LocalDocumentTestCase(TestCase):
	def setUp(self):
		self.client = Client()
		self.schedule = Schedule.objects.all()[0]

	def test_get_documents(self):
		response = self.client.get("schedule/{0}/documents/local/")
		self.assertEqual(response.status_code, 200)