import unittest

from bjt_bias.app import create_app, fmt_current, fmt_voltage

HANDOUT = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
           "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
           "beta": "100", "vbe": "0.7"}


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
        self.assertIn("3.01746 mA", body)   # IC, 6 significant figures
        self.assertIn("7.55489 V", body)    # VCE
        self.assertIn("Active", body)


class TestFormatting(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_current_units(self):
        self.assertEqual(fmt_current(1.5), "1.5 A")
        self.assertEqual(fmt_current(0.00122986), "1.22986 mA")
        self.assertEqual(fmt_current(1.22986e-05), "12.2986 µA")
        self.assertEqual(fmt_current(1.2345e-08), "12.345 nA")
        self.assertEqual(fmt_current(0.0), "0 A")

    def test_voltage_six_significant_figures(self):
        self.assertEqual(fmt_voltage(8.0521605), "8.05216 V")

    def test_handout_sample_renders_in_milliamps(self):
        body = self.client.post("/", data=HANDOUT).get_data(as_text=True)
        self.assertIn("1.22986 mA", body)
        self.assertIn("12.2986 µA", body)
        self.assertIn("8.05216 V", body)

    def test_cutoff_currents_render_as_zero(self):
        data = {**HANDOUT, "r2": "1", "r2_unit": "kohm"}
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn("0 A", body)


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


class TestLayout(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_post_without_unit_keys_computes_and_shows_ohms(self):
        body = self.client.post("/", data=BASE).get_data(as_text=True)
        self.assertIn("3.01746 mA", body)
        self.assertIn('<option value="ohm" selected>', body)
        self.assertEqual(body.count('<option value="ohm" selected>'), 4)

    def test_page_contains_circuit_schematic(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("<svg", body)
        self.assertIn('class="schematic"', body)
        for label in ("VCC", "R1", "R2", "RC", "RE", "Q1", "GND"):
            with self.subTest(label=label):
                self.assertIn(f">{label}<", body)

    def test_unit_selects_default_to_kilo_ohms(self):
        body = self.client.get("/").get_data(as_text=True)
        for field in ("r1", "r2", "rc", "re"):
            self.assertIn(f'name="{field}_unit"', body)
        self.assertEqual(body.count('<option value="kohm" selected>'), 4)

    def test_unit_selection_is_preserved_after_submit(self):
        data = {**HANDOUT, "r1_unit": "ohm", "r1": "10000"}
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn('<option value="ohm" selected>', body)

    def test_cutoff_badge_and_zero_currents(self):
        data = {**HANDOUT, "r2": "1", "r2_unit": "kohm"}
        body = self.client.post("/", data=data).get_data(as_text=True)
        self.assertIn("Cutoff", body)
        self.assertIn("region-cutoff", body)
        self.assertIn("ตรวจทานอิสระ: ผ่าน", body)
        self.assertNotIn("ไม่ผ่าน", body)

    def test_section_headings_match_handout(self):
        body = self.client.get("/").get_data(as_text=True)
        self.assertIn("Input Parameters", body)
        body = self.client.post("/", data=HANDOUT).get_data(as_text=True)
        for heading in ("DC Bias Results", "Operating Region"):
            with self.subTest(heading=heading):
                self.assertIn(heading, body)
