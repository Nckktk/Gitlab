import math
import unittest

from bjt_bias.engineering import (
    VCE_SAT,
    BiasInputs,
    analyze,
    cross_check,
    parse_inputs,
    solve_nodal,
    solve_thevenin,
)

VALID = {"vcc": "12", "r1": "10000", "r2": "2200", "rc": "1000",
         "re": "470", "beta": "150", "vbe": "0.7"}
HAND = BiasInputs(vcc=12, r1=10000, r2=2200, rc=1000, re=470, beta=150, vbe=0.7)


class TestParseInputs(unittest.TestCase):
    def test_accepts_valid(self):
        inputs, errors = parse_inputs(VALID)
        self.assertEqual(errors, {})
        self.assertEqual(inputs, HAND)

    def test_rejects_blank(self):
        _, errors = parse_inputs({**VALID, "vcc": ""})
        self.assertIn("vcc", errors)

    def test_rejects_text(self):
        _, errors = parse_inputs({**VALID, "r1": "abc"})
        self.assertIn("r1", errors)

    def test_rejects_comma_decimal(self):
        _, errors = parse_inputs({**VALID, "vbe": "0,7"})
        self.assertIn("vbe", errors)

    def test_rejects_missing_field(self):
        raw = dict(VALID)
        del raw["beta"]
        _, errors = parse_inputs(raw)
        self.assertIn("beta", errors)

    def test_rejects_zero_and_negative_resistance(self):
        for field in ("r1", "r2", "rc", "re"):
            with self.subTest(field=field):
                _, errors = parse_inputs({**VALID, field: "0"})
                self.assertIn(field, errors)
                _, errors = parse_inputs({**VALID, field: "-1"})
                self.assertIn(field, errors)

    def test_rejects_bad_beta_and_vbe(self):
        self.assertIn("beta", parse_inputs({**VALID, "beta": "0"})[1])
        self.assertIn("beta", parse_inputs({**VALID, "beta": "-5"})[1])
        self.assertIn("vbe", parse_inputs({**VALID, "vbe": "-0.1"})[1])
        self.assertIn("vbe", parse_inputs({**VALID, "vbe": "12"})[1])

    def test_rejects_non_finite(self):
        for bad in ("nan", "inf", "-inf"):
            with self.subTest(bad=bad):
                _, errors = parse_inputs({**VALID, "vcc": bad})
                self.assertIn("vcc", errors)


class TestThevenin(unittest.TestCase):
    def test_hand_worked_example(self):
        r = solve_thevenin(HAND)
        self.assertTrue(math.isclose(r["vbb"], 2.163934, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["rb"], 1803.278689, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["ib"], 2.011637e-5, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["ic"], 3.017456e-3, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["ie"], 3.037573e-3, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["ve"], 1.427659, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["vc"], 8.982544, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["vce"], 7.554885, rel_tol=1e-5))

    def test_different_inputs_give_different_results(self):
        a = solve_thevenin(HAND)
        b = solve_thevenin(BiasInputs(vcc=9, r1=47000, r2=10000,
                                      rc=2200, re=1000, beta=100, vbe=0.7))
        self.assertNotAlmostEqual(a["ic"], b["ic"])


class TestNodalAndCheck(unittest.TestCase):
    def test_nodal_matches_hand_example(self):
        r = solve_nodal(HAND)
        self.assertTrue(math.isclose(r["ve"], 1.427659, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["ic"], 3.017456e-3, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["vce"], 7.554885, rel_tol=1e-5))
        self.assertTrue(math.isclose(r["vb"], r["ve"] + 0.7, rel_tol=1e-9))

    def test_methods_agree_on_three_inputs(self):
        cases = [
            HAND,
            BiasInputs(vcc=9, r1=47000, r2=10000, rc=2200, re=1000, beta=100, vbe=0.7),
            BiasInputs(vcc=5, r1=3300, r2=680, rc=470, re=100, beta=300, vbe=0.65),
        ]
        for case in cases:
            with self.subTest(case=case):
                passed, diff = cross_check(solve_thevenin(case), solve_nodal(case))
                self.assertTrue(passed)
                self.assertLessEqual(diff, 1e-9)

    def test_check_detects_deliberate_mismatch(self):
        raw = solve_thevenin(HAND)
        perturbed = dict(raw, ic=raw["ic"] * 1.001)
        passed, diff = cross_check(raw, perturbed)
        self.assertFalse(passed)
        self.assertGreater(diff, 1e-6)

    def test_check_handles_zero_together(self):
        a = {"ic": 0.0, "vce": 0.0}
        b = {"ic": 0.0, "vce": 0.0}
        self.assertEqual(cross_check(a, b), (True, 0.0))


CUTOFF = BiasInputs(vcc=12, r1=100000, r2=1000, rc=1000, re=1000, beta=100, vbe=0.7)
SATURATED = BiasInputs(vcc=12, r1=47000, r2=10000, rc=4700, re=10, beta=150, vbe=0.7)


class TestAnalyze(unittest.TestCase):
    def test_active_region(self):
        r = analyze(HAND)
        self.assertEqual(r.region, "active")
        self.assertIsNone(r.warning)
        self.assertTrue(r.check_passed)

    def test_cutoff_reports_zero_currents(self):
        r = analyze(CUTOFF)
        self.assertEqual(r.region, "cutoff")
        self.assertEqual((r.ib, r.ic, r.ie), (0.0, 0.0, 0.0))
        self.assertEqual(r.ve, 0.0)
        self.assertEqual(r.vc, 12.0)
        self.assertEqual(r.vce, 12.0)
        self.assertTrue(r.check_passed)

    def test_saturation_warns_and_keeps_raw_values(self):
        r = analyze(SATURATED)
        self.assertEqual(r.region, "saturation")
        self.assertIsNotNone(r.warning)
        self.assertLessEqual(r.vce, VCE_SAT)
        self.assertTrue(r.check_passed)

    def test_large_beta_does_not_crash(self):
        r = analyze(BiasInputs(vcc=12, r1=10000, r2=2200, rc=1000,
                               re=470, beta=1e6, vbe=0.7))
        self.assertTrue(math.isfinite(r.ic))
        self.assertTrue(math.isfinite(r.vce))


if __name__ == "__main__":
    unittest.main()
