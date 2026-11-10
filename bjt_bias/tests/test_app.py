import unittest

from bjt_bias.app import create_app


class TestApp(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_get_form(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn('name="vcc"', resp.get_data(as_text=True))

    def test_post_valid_shows_operating_point(self):
        resp = self.client.post("/", data={
            "vcc": "12", "r1": "10000", "r2": "2200", "rc": "1000",
            "re": "470", "beta": "150", "vbe": "0.7",
        })
        body = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("0.00301746", body)   # IC, 6 significant figures
        self.assertIn("7.55489", body)      # VCE
        self.assertIn("Active", body)
