import unittest

import app


class QualityRegressionTests(unittest.TestCase):
    def setUp(self):
        app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = app.app.test_client()

    def test_health_contract_is_public_and_safe(self):
        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get_json(),
            {"service": "ConferenceFlow", "status": "ok"},
        )

    def test_unknown_route_returns_safe_not_found_response(self):
        response = self.client.get("/route-that-does-not-exist")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {"error": "Not found"})

    def test_logout_requires_post(self):
        response = self.client.get("/logout")

        self.assertEqual(response.status_code, 405)


if __name__ == "__main__":
    unittest.main()
