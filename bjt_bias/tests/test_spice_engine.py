import tempfile
import unittest
from pathlib import Path
from unittest import mock

from bjt_bias.spice_engine import (
    DEFAULT_BJT_MODEL_NAME,
    SpiceError,
    SpiceRunConfig,
    build_ce_netlist,
    parse_ac_output,
    parse_op_output,
    parse_tran_output,
    run_analysis,
)


CFG = SpiceRunConfig(
    vcc=12, r1=100e3, r2=22e3, rc=2.2e3, re=1e3, rl=10e3,
    cin=10e-6, cout=10e-6, beta=100, vbe=0.7, amplitude_mv=10, frequency_hz=1000,
)


class TestNetlist(unittest.TestCase):
    def test_build_op_netlist_has_required_parts(self):
        net = build_ce_netlist(CFG, "op")
        self.assertIn("VCC vcc 0 DC 12", net)
        self.assertIn("R1 vcc b 100000", net)
        self.assertIn("Q1 c b e Q2N3904_GENERIC", net)
        self.assertIn("\nop\n", net)
        self.assertIn("i(vcc)", net)
        self.assertIn(".endc", net)

    def test_build_ac_and_tran(self):
        ac = build_ce_netlist(CFG, "ac")
        self.assertIn("ac dec", ac)
        self.assertIn("wrdata ac_output.txt v(out)", ac)
        tr = build_ce_netlist(CFG, "tran")
        self.assertIn("tran", tr)
        self.assertIn("SIN(", tr)
        self.assertIn("wrdata tran_output.txt v(in) v(out)", tr)


class TestParsers(unittest.TestCase):
    def test_parse_op_output(self):
        log = """
v(b) = 1.800000e+00
v(e) = 1.100000e+00
v(c) = 7.600000e+00
v(c,e) = 6.500000e+00
i(vcc) = -2.00000e-03
"""
        op = parse_op_output(log)
        self.assertAlmostEqual(op["vb"], 1.8)
        self.assertAlmostEqual(op["vce"], 6.5)
        self.assertAlmostEqual(op["ic"], 0.002)

    def test_parse_ac_wrdata_4col(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ac_output.txt"
            p.write_text("1.000000e+01  1.000000e+00  1.000000e+01  0.000000e+00\n"
                         "1.000000e+03  1.000000e+01  1.000000e+03  0.000000e+00\n", encoding="utf-8")
            ac = parse_ac_output(Path(td))
            self.assertEqual(len(ac["frequency_hz"]), 2)
            self.assertAlmostEqual(ac["gain_db"][0], 0.0, places=5)
            self.assertAlmostEqual(ac["gain_db"][1], 20.0, places=5)

    def test_parse_tran_wrdata_4col(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "tran_output.txt"
            p.write_text("0.000000e+00  0.000000e+00  0.000000e+00  5.000000e+00\n"
                         "1.000000e-03  1.000000e-02  1.000000e-03 -1.000000e+00\n", encoding="utf-8")
            tr = parse_tran_output(Path(td))
            self.assertEqual(tr["vin_v"][1], 0.01)
            self.assertEqual(tr["vout_v"][1], -1.0)


class TestRunAnalysis(unittest.TestCase):
    def test_missing_ngspice_raises(self):
        with mock.patch("bjt_bias.spice_engine.ngspice_available", return_value=False):
            with self.assertRaises(SpiceError):
                run_analysis(CFG, "op")

    def test_run_analysis_parses_op_with_mocked_subprocess(self):
        def fake_run(cmd, cwd=None, capture_output=True, text=True, timeout=None, check=False):
            log_path = Path(cwd) / "run.log"
            log_path.write_text(
                "v(b) = 1.8\nv(e) = 1.1\nv(c) = 7.6\nv(c,e) = 6.5\ni(vcc) = -2e-3\n", encoding="utf-8"
            )
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch("bjt_bias.spice_engine.ngspice_available", return_value=True), \
             mock.patch("bjt_bias.spice_engine.ngspice_version", return_value="ngspice 42"), \
             mock.patch("bjt_bias.spice_engine.subprocess.run", side_effect=fake_run):
            result = run_analysis(CFG, "op")
        self.assertEqual(result["analysis"], "op")
        self.assertAlmostEqual(result["op"]["ic"], 0.002)
        self.assertEqual(result["engine"], "ngspice")


class TestAppSpiceIntegration(unittest.TestCase):
    def test_spice_run_missing_ngspice_shows_error_not_success(self):
        from bjt_bias.app import create_app
        client = create_app().test_client()
        data = {
            "mode": "divider", "vcc": "12", "r1": "100", "r1_unit": "kohm",
            "r2": "22", "r2_unit": "kohm", "rc": "2.2", "rc_unit": "kohm",
            "re": "1", "re_unit": "kohm", "beta": "100", "vbe": "0.7",
            "rl": "10", "rl_unit": "kohm", "cin_u": "10", "cout_u": "10",
            "amplitude_mv": "10", "frequency_hz": "1000", "spice_analysis": "op",
            "run_spice": "1",
        }
        with mock.patch("bjt_bias.spice_engine.ngspice_available", return_value=False), \
             mock.patch("bjt_bias.app.ngspice_available", return_value=False), \
             mock.patch("bjt_bias.app.ngspice_version", return_value=None):
            resp = client.post("/", data=data)
        body = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("SPICE Error", body)
        self.assertNotIn("Success", body)

    def test_spice_result_rendered_from_mock(self):
        from bjt_bias.app import create_app
        client = create_app().test_client()
        data = {
            "mode": "divider", "vcc": "12", "r1": "100", "r1_unit": "kohm",
            "r2": "22", "r2_unit": "kohm", "rc": "2.2", "rc_unit": "kohm",
            "re": "1", "re_unit": "kohm", "beta": "100", "vbe": "0.7",
            "rl": "10", "rl_unit": "kohm", "cin_u": "10", "cout_u": "10",
            "amplitude_mv": "10", "frequency_hz": "1000", "spice_analysis": "op",
            "run_spice": "1",
        }
        fake = {
            "analysis": "op", "engine": "ngspice", "engine_version": "ngspice 42",
            "model_name": DEFAULT_BJT_MODEL_NAME, "netlist": "* net", "log_tail": "ok",
            "op": {"vb": 1.8, "ve": 1.1, "vc": 7.6, "vce": 6.5, "ic": 0.002},
        }
        with mock.patch("bjt_bias.app.run_analysis", return_value=fake), \
             mock.patch("bjt_bias.app.ngspice_available", return_value=True), \
             mock.patch("bjt_bias.app.ngspice_version", return_value="ngspice 42"):
            resp = client.post("/", data=data)
        body = resp.get_data(as_text=True)
        self.assertEqual(resp.status_code, 200)
        self.assertIn("VB (SPICE)", body)
        self.assertIn("2 mA", body)
        self.assertIn("Success", body)


if __name__ == "__main__":
    unittest.main()
