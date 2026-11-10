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


BASE = {"vcc": "12", "r1": "10000", "r2": "2200", "rc": "1000",
        "re": "470", "beta": "150", "vbe": "0.7"}


class TestAppValidation(TestApp):
    def test_blank_field_shows_error_and_keeps_values(self):
        resp = self.client.post("/", data={**BASE, "r1": ""})
        body = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ต้องเป็นตัวเลข", body)
        self.assertIn('value="2200"', body)

    def test_zero_resistance_is_not_a_crash(self):
        resp = self.client.post("/", data={**BASE, "re": "0"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("มากกว่าศูนย์", resp.get_data(as_text=True))

    def test_text_and_comma_decimal_rejected(self):
        resp = self.client.post("/", data={**BASE, "vbe": "0,7"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("ต้องเป็นตัวเลข", resp.get_data(as_text=True))

    def test_vbe_not_less_than_vcc(self):
        resp = self.client.post("/", data={**BASE, "vbe": "12"})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("น้อยกว่า VCC", resp.get_data(as_text=True))

    def test_saturation_warning_visible(self):
        resp = self.client.post("/", data={**BASE, "r1": "47000", "r2": "10000",
                                            "rc": "4700", "re": "10"})
        body = resp.get_data(as_text=True)
        self.assertIn("Saturation", body)
        self.assertIn("ไม่ทำงานใน active region", body)

    def test_huge_value_rejected_not_nan(self):
        resp = self.client.post("/", data={**BASE, "beta": "1e308"})
        body = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("มากเกินไป", body)
        self.assertNotIn("nan", body)
