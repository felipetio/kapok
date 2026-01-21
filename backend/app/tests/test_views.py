from django.test import Client, TestCase


class SimpleTest(TestCase):
    def setUp(self):
        # Every test needs a client.
        self.client = Client()

    def test_details(self):
        # Issue a GET request.
        response = self.client.get("/")

        # Check that the response is 200 OK.
        self.assertEqual(response.status_code, 200)
