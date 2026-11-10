# BJT Bias UI Match — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restyle the BJT DC bias page to the handout's Lab 2 target screen: card layout, inline SVG circuit schematic, `DC Bias Results` table with currents in mA/µA, and a per-resistor Ω/kΩ selector.

**Architecture:** The engineering module stays pure SI (Ω, A, V) and gains unit-aware parsing of `{field}_unit` keys. Formatting lives in `app.py` as two Jinja filters. `index.html` carries the layout and a hand-drawn inline SVG; `style.css` is rewritten for the card/grid look. No JavaScript, no new dependency.

**Tech Stack:** Python 3.12, Flask 3.1, Jinja2, unittest run by pytest.

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-ui-design.md`

## Global Constraints

- No JavaScript anywhere; the page must work fully with JS disabled.
- No new runtime dependency: Flask + pytest only.
- `bjt_bias/engineering.py` must never import Flask.
- `BiasInputs` holds SI base units: Ω, A, V.
- Numeric display: 6 significant figures (`%.6g`); voltages `V`, currents auto-scaled A/mA/µA/nA.
- Section headings English (`Input Parameters`, `Circuit`, `DC Bias Results`, `Operating Region`); helper text, errors and warnings Thai.
- Keep every existing behaviour: per-field errors, preserved form values, cutoff/saturation overrides, cross-check line.
- Do not modify root `electrical.py`, `test_electrical.py`, `README.md`.
- `python -m pytest -q` from the repo root must end green.
- Work on a branch; merge to `main`; push.

## Review Focus

1. A POST that omits `*_unit` keys (old direct calls, curl, tests) must still mean Ω, exactly as before.
2. A tampered or empty unit string (`r1_unit=mohm`) must give a per-field readable error, never a crash and never a silent Ω assumption for garbage.
3. A kΩ value that converts past the input limit (`1e10` kΩ → `1e13` Ω) must be rejected as `ค่ามากเกินไป`, never produce `inf`/`nan`.
4. Cutoff inputs must show currents as `0 A` and the `Cutoff` badge, and the independent check must still read `ผ่าน`.
5. A tiny but nonzero current (e.g. `1.2345e-8 A`) must render in µA/nA, never as `0 A`.

---

### Task 1: Unit-aware input parsing

**Files:**
- Modify: `bjt_bias/engineering.py` (constants near line 9-15, loop at line 29-67)
- Test: `bjt_bias/tests/test_engineering.py`

**Interfaces:**
- Consumes: existing `BiasInputs`, `FIELDS`, `MAX_INPUT`, `_NUMBER_ERROR`, `_POSITIVE_ERROR`, `_TOO_LARGE_ERROR`.
- Produces: `RESISTOR_FIELDS = ("r1", "r2", "rc", "re")`, `UNIT_OHM = "ohm"`, `UNIT_KOHM = "kohm"`, `UNIT_FACTORS = {"ohm": 1.0, "kohm": 1e3}`, `_UNIT_ERROR = "หน่วยไม่ถูกต้อง"`. `parse_inputs(raw: dict[str, str]) -> tuple[BiasInputs | None, dict[str, str]]` keeps its signature and reads `raw.get(f"{field}_unit")` for every field in `RESISTOR_FIELDS`.

- [ ] **Step 1: Write the failing tests**

Append to `TestParseInputs` in `bjt_bias/tests/test_engineering.py`:

```python
    def test_kohm_unit_scales_to_ohms(self):
        inputs, errors = parse_inputs(
            {**VALID, "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
             "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm"}
        )
        self.assertEqual(errors, {})
        self.assertEqual(
            (inputs.r1, inputs.r2, inputs.rc, inputs.re),
            (100000.0, 22000.0, 2200.0, 1000.0),
        )

    def test_missing_unit_keys_mean_ohms(self):
        inputs, errors = parse_inputs(VALID)
        self.assertEqual(errors, {})
        self.assertEqual(inputs.r1, 10000.0)

    def test_unknown_unit_is_rejected_per_field(self):
        _, errors = parse_inputs({**VALID, "r1_unit": "mohm"})
        self.assertEqual(errors.get("r1"), "หน่วยไม่ถูกต้อง")

    def test_kohm_value_over_limit_is_rejected(self):
        _, errors = parse_inputs({**VALID, "r1": "1e10", "r1_unit": "kohm"})
        self.assertEqual(errors.get("r1"), "ค่ามากเกินไป")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest bjt_bias\tests\test_engineering.py -q`
Expected: 4 failures — `r1` is `100.0` not `100000.0`, and `mohm` / `1e10` are accepted.

- [ ] **Step 3: Implement unit handling in `parse_inputs`**

Inside the per-field loop, for each `field` in `RESISTOR_FIELDS`: read `unit = (raw.get(f"{field}_unit") or UNIT_OHM).strip()`; if `unit not in UNIT_FACTORS`, set `errors[field] = _UNIT_ERROR` and continue; otherwise multiply the parsed number by `UNIT_FACTORS[unit]` **before** the `math.isfinite` and `abs(value) > MAX_INPUT` checks. Fields outside `RESISTOR_FIELDS` use a factor of `1.0`.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m pytest bjt_bias\tests -q`
Expected: PASS, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/engineering.py bjt_bias/tests/test_engineering.py
git commit -m "feat: accept resistor units in ohms or kilo-ohms"
```

---

### Task 2: Current/voltage display filters

**Files:**
- Modify: `bjt_bias/app.py` (`create_app`, whole file is 26 lines)
- Modify: `bjt_bias/templates/index.html:44-50` (results table cells)
- Test: `bjt_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `analyze`, `parse_inputs`; `result.ib/.ic/.ie/.vb/.ve/.vc/.vce` floats in SI.
- Produces: `fmt_current(amps: float) -> str` and `fmt_voltage(volts: float) -> str` in `bjt_bias/app.py`, registered as Jinja filters `current` and `voltage` in `create_app()`.

- [ ] **Step 1: Write the failing tests**

Add to `bjt_bias/tests/test_app.py`:

```python
from bjt_bias.app import create_app, fmt_current, fmt_voltage

HANDOUT = {"vcc": "12", "r1": "100", "r2": "22", "rc": "2.2", "re": "1",
           "r1_unit": "kohm", "r2_unit": "kohm", "rc_unit": "kohm", "re_unit": "kohm",
           "beta": "100", "vbe": "0.7"}


class TestFormatting(unittest.TestCase):
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
```

`TestFormatting` needs a `client`; give it `setUp` identical to `TestApp.setUp` (`self.client = create_app().test_client()`).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest bjt_bias\tests\test_app.py -q`
Expected: collection error / `ImportError: cannot import name 'fmt_current'`.

- [ ] **Step 3: Implement the two filters and use them in the template**

`fmt_current`: `abs(amps) >= 1e-3` → `"%.6g mA" % (amps * 1e3)`; `>= 1e-6` → µA; `>= 1e-9` → nA; else `"%.6g A" % amps`. `fmt_voltage`: `"%.6g V" % volts`. Register with `app.add_template_filter(fmt_current, "current")` and `app.add_template_filter(fmt_voltage, "voltage")`.

In `index.html` replace the seven `"%.6g"|format(...)` cells with `{{ result.ib|current }}` etc. for IB/IC/IE and `{{ result.vb|voltage }}` etc. for VB/VE/VC/VCE.

Then update the two existing assertions in `TestApp` that pin the old A notation (`0.00301746` → `3.01746 mA`, and likewise for VCE if the string changed).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv\Scripts\python -m pytest bjt_bias\tests -q`
Expected: PASS, 0 failures.

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/tests/test_app.py
git commit -m "feat: display bias currents in engineering units"
```

---

### Task 3: Handout-style layout, schematic and unit selectors

**Files:**
- Modify: `bjt_bias/templates/index.html` (full rewrite of the body)
- Modify: `bjt_bias/static/style.css` (full rewrite)
- Test: `bjt_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `current` / `voltage` filters from Task 2; `errors`, `form`, `result` context keys; `result.region`, `result.warning`, `result.check_passed`, `result.check_max_rel_diff`; unit values `ohm` / `kohm` from Task 1.
- Produces: `<svg class="schematic" role="img">` with labels `VCC`, `R1`, `R2`, `RC`, `RE`, `Q1`, `GND`; one `<select name="{field}_unit">` per resistor field, each rendering `kohm` selected on GET; region badge markup `class="region region-{region}"`; results values paired with their labels.

- [ ] **Step 1: Write the failing tests**

Add to `bjt_bias/tests/test_app.py`:

```python
class TestLayout(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

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
        self.assertIn("ผ่าน", body)

    def test_section_headings_match_handout(self):
        body = self.client.get("/").get_data(as_text=True)
        for heading in ("Input Parameters", "DC Bias Results", "Operating Region"):
            with self.subTest(heading=heading):
                self.assertIn(heading, body)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv\Scripts\python -m pytest bjt_bias\tests\test_app.py -q`
Expected: 5 failures — no `<svg>`, no unit selects, headings absent.

- [ ] **Step 3: Rewrite `index.html` body and `style.css`**

`index.html`: header bar with `BJT DC Bias Calculator` and `ENG29 2121 · Lab 2`; a `.layout` grid holding the `Input Parameters` card (7 labelled fields, each resistor field followed by its `<select name="{field}_unit">` with `<option value="ohm">Ω</option>` and `<option value="kohm" selected>kΩ</option>`, no `selected` on `ohm` unless `form.get(field ~ '_unit') == 'ohm'`; inline errors preserved) and the `Circuit` card holding the inline SVG (`viewBox="0 0 380 320"`, `role="img"`, `<title>` describing the voltage-divider bias, stroke via `class="wire"`/`class="component"`, node dots, transistor drawn as circle + base bar + arrow on the emitter); then a full-width results card headed `DC Bias Results` with the seven values and an `Operating Region` badge plus Thai subtitle, the existing warning block, and the existing cross-check line.

`style.css`: light paper background, white cards with 1px border and 10px radius, max-width 1080px, `.layout` two columns above 860px and one below, `.schematic` full width with `currentColor` strokes, `.region-active` green, `.region-saturation` amber, `.region-cutoff` grey — each badge with a visible label, not colour alone.

- [ ] **Step 4: Run the full suite to verify it passes**

Run: `python -m pytest -q`
Expected: PASS, 0 failures.

- [ ] **Step 5: Check the rendered page by hand**

Run: `.venv\Scripts\python -m flask --app bjt_bias.app run --no-reload --port 5000`
Expected: `GET /` shows the form, the schematic and the three headings; posting `VCC=12, R1=100 k, R2=22 k, RC=2.2 k, RE=1 k, β=100, VBE=0.7` shows `IC 1.22986 mA`, `VCE 8.05216 V`, `Active`.

- [ ] **Step 6: Commit**

```bash
git add bjt_bias/templates/index.html bjt_bias/static/style.css bjt_bias/tests/test_app.py
git commit -m "feat: lay out the page like the Lab 2 target screen"
```

---

### Task 4: README — units, assumptions, run notes

**Files:**
- Modify: `bjt_bias/README.md`
- Test: none (documentation); verification is the full suite plus a read-back.

**Interfaces:**
- Consumes: the behaviour shipped in Tasks 1-3.
- Produces: documentation of unit conversion, display units, model assumptions and the debug-server warning.

- [ ] **Step 1: Update `bjt_bias/README.md`**

Add: (a) a units table stating resistor inputs are Ω or kΩ with kΩ multiplied by 1000 before solving, and currents display in A/mA/µA/nA at 6 significant figures; (b) a `แบบจำลอง` section listing constant β, constant VBE, no Early effect, forward-active approximation, and that the schematic is decorative (it does not redraw to scale); (c) the handout sample re-expressed in kΩ (`12 V, 100 kΩ, 22 kΩ, 2.2 kΩ, 1 kΩ, β=100, VBE=0.70 V`) with the resulting `IC = 1.22986 mA`, `VCE = 8.05216 V`; (d) a one-line warning that `app.run(debug=True)` must never be exposed beyond localhost.

- [ ] **Step 2: Verify the suite is still green**

Run: `python -m pytest -q`
Expected: PASS, 0 failures.

- [ ] **Step 3: Commit**

```bash
git add bjt_bias/README.md
git commit -m "docs: document units, model assumptions and run notes"
```

---

## Self-Review

- Spec coverage: units selector (Task 1 + Task 3), current display in mA/µA (Task 2), schematic + layout + headings + badge (Task 3), docs and assumptions (Task 4). No spec item lacks a task.
- Step scan: each step names the test or the artifact; SVG geometry and CSS spacing are explicitly left to the implementer by the spec.
- Type consistency: `parse_inputs` signature unchanged; filters are `fmt_current` / `fmt_voltage` registered as `current` / `voltage`; unit values `ohm` / `kohm` used identically in Task 1 and Task 3.
- Review Focus: items 1-3 pinned in Task 1 tests, items 4-5 in Task 2/3 tests.
