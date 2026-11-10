# BJT Common-Emitter DC Bias — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Flask เว็บแอปหน้าเดียวที่คำนวณ DC operating point ของวงจรไบแอส BJT common-emitter พร้อม validation, region warning และการตรวจทานด้วยสมการอิสระ

**Architecture:** แยก `engineering.py` (สูตรบริสุทธิ์ ไม่รู้จัก Flask) ออกจาก `app.py` (route + form parsing เท่านั้น) โดย `analyze()` เรียกสอง solver (Thevenin, nodal) เทียบผลดิบก่อน แล้วจึงปรับค่าตาม region ก่อนส่งให้ Jinja render

**Tech Stack:** Python 3.12.7, Flask 3.x, pytest 8.x, Jinja2, HTML/CSS ธรรมดา (ไม่มี JavaScript)

**Spec:** `docs/superpowers/specs/2026-11-10-bjt-dc-bias-design.md`

## Global Constraints

- Python 3.12.7 บน Windows, virtualenv ที่ `.venv/` (ถูก gitignore แล้ว)
- dependency มีเพียง `Flask>=3.0,<4` และ `pytest>=8,<9`
- โค้ดทั้งหมดอยู่ใต้ `bjt_bias/` ห้ามแก้ `electrical.py`, `test_electrical.py`, `README.md` ที่ root
- หน่วย SI: A และ V, แสดงผลด้วย `format(value, ".6g")` (6 significant figures) ห้ามใช้ µA/mA prefix
- `VCE_SAT = 0.2` V
- ลำดับใน `analyze()`: raw solvers → `cross_check` → region override
- cutoff รายงาน `ib=ic=ie=0`, `ve=0`, `vc=vcc`, `vce=vcc`
- relative tolerance ของ cross-check = `1e-9`, ตัวส่วน `max(|a|,|b|,1e-12)`
- UI ภาษาไทย, ชื่อฟิลด์ฟอร์ม: `vcc, r1, r2, rc, re, beta, vbe`
- ทำงานบน branch `feat/bjt-dc-bias` แล้ว merge เข้า `main` และ push `origin/main` วันนี้
- ใช้ `python -m pytest bjt_bias/tests -q` จาก repo root (คำสั่งนี้ใส่ cwd ใน `sys.path` ทำให้ import `bjt_bias` ได้)

## Review Focus

1. `VBE >= VCC` หรือ `VBE < 0` → ต้องถูกปฏิเสธพร้อม error รายฟิลด์ ไม่ใช่ปล่อยให้ได้กระแสติดลบหรือ `VE` เพี้ยน
2. `R1/R2/RC/RE` เป็นศูนย์หรือติดลบ → ต้องไม่เกิด `ZeroDivisionError`/traceback แต่ต้องขึ้น error ที่อ่านรู้เรื่อง
3. `beta` ใหญ่มากหรือ `RC` ใหญ่มาก → ต้องไม่ crash/overflow และยังติด label saturation ได้ถูก
4. อินพุต cutoff (`VBB < VBE`) → ต้องรายงานกระแสเป็นศูนย์และ `VCE = VCC` ไม่ใช่ค่าติดลบ และ `check` ต้องยัง PASS
5. ค่าว่าง / ตัวอักษร / ทศนิยมลูกน้ำ (`12,5`) → error รายฟิลด์, HTTP 200, ค่าที่กรอกยังอยู่บนฟอร์ม

---

## Task 1: Environment + validation + Thevenin solver

**Files:**
- Create: `bjt_bias/requirements.txt`
- Create: `bjt_bias/__init__.py` (ไฟล์ว่าง)
- Create: `bjt_bias/tests/__init__.py` (ไฟล์ว่าง)
- Create: `bjt_bias/engineering.py`
- Create: `bjt_bias/tests/test_engineering.py`

**Interfaces:**
- Consumes: ไม่มี
- Produces:
  - `BiasInputs(vcc, r1, r2, rc, re, beta, vbe)` — frozen dataclass, ฟิลด์เป็น `float`
  - `parse_inputs(raw: dict[str, str]) -> tuple[BiasInputs | None, dict[str, str]]` — คืน `(inputs, errors)`; `errors` ว่างแปลว่าผ่าน, key คือชื่อฟิลด์
  - `solve_thevenin(i: BiasInputs) -> dict[str, float]` — key: `"vbb", "rb", "ib", "ic", "ie", "vb", "ve", "vc", "vce"`
  - `VCE_SAT = 0.2`

- [ ] **Step 1: สร้าง venv และติดตั้ง dependency**

`bjt_bias/requirements.txt`:
```
Flask>=3.0,<4
pytest>=8,<9
```

Run:
```
python -m venv .venv
.venv\Scripts\python -m pip install -r bjt_bias/requirements.txt
```
Expected: `Successfully installed Flask-3… pytest-8…`

- [ ] **Step 2: เขียน test ที่ยังไม่ผ่าน**

`bjt_bias/tests/test_engineering.py`:
```python
import math
import unittest

from bjt_bias.engineering import BiasInputs, parse_inputs, solve_thevenin

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
```

- [ ] **Step 3: รัน test ให้เห็นว่า fail**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_bias.engineering'`

- [ ] **Step 4: เขียน `bjt_bias/engineering.py`**

```python
import math
from dataclasses import dataclass

VCE_SAT = 0.2
FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")


@dataclass(frozen=True)
class BiasInputs:
    vcc: float
    r1: float
    r2: float
    rc: float
    re: float
    beta: float
    vbe: float


def parse_inputs(raw: dict[str, str]) -> tuple[BiasInputs | None, dict[str, str]]:
    """แปลงและตรวจค่าดิบจากฟอร์ม คืน (inputs, errors)"""
```

กติกาการ validate (ต้องตรงกับ test ทุกข้อ): ฟิลด์หาย/ว่าง → error; `float()` ไม่ผ่าน (รวม `"12,5"`) → error; `not math.isfinite` → error; `vcc <= 0`, `r1/r2/rc/re <= 0`, `beta <= 0`, `vbe < 0`, `vbe >= vcc` → error

```python
def solve_thevenin(i: BiasInputs) -> dict[str, float]:
    """แก้ด้วย Thevenin equivalent ตาม spec §4"""
```

- [ ] **Step 5: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: PASS (11 tests)

- [ ] **Step 6: Commit**

```bash
git add bjt_bias/requirements.txt bjt_bias/__init__.py bjt_bias/tests/__init__.py bjt_bias/engineering.py bjt_bias/tests/test_engineering.py
git commit -m "feat: validate BJT bias inputs and solve via Thevenin"
```

---

## Task 2: Nodal solver + independent cross-check

**Files:**
- Modify: `bjt_bias/engineering.py`
- Modify: `bjt_bias/tests/test_engineering.py`

**Interfaces:**
- Consumes: `BiasInputs`, `solve_thevenin` จาก Task 1
- Produces:
  - `solve_nodal(i: BiasInputs) -> dict[str, float]` — key ชุดเดียวกับ `solve_thevenin`, ใช้ `vb = ve + vbe`
  - `cross_check(a: dict[str, float], b: dict[str, float]) -> tuple[bool, float]` — เทียบ `ic` และ `vce`, คืน `(passed, max_rel_diff)`; `REL_TOL = 1e-9`
  - `REL_TOL = 1e-9`

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

เพิ่มใน `bjt_bias/tests/test_engineering.py`:
```python
from bjt_bias.engineering import cross_check, solve_nodal


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
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: FAIL — `ImportError: cannot import name 'cross_check'`

- [ ] **Step 3: เพิ่ม `solve_nodal` และ `cross_check` ใน `bjt_bias/engineering.py`**

`cross_check` ใช้ตัวส่วนนี้ (ห้ามเปลี่ยน):
```python
REL_TOL = 1e-9

def _rel_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-12)

def cross_check(a, b) -> tuple[bool, float]:
    diff = max(_rel_diff(a["ic"], b["ic"]), _rel_diff(a["vce"], b["vce"]))
    return (diff <= REL_TOL, diff)
```

`solve_nodal`: ตั้ง KCL ที่โหนด B/E ตาม spec §4 แก้สมการเดียวใน `ve` แล้วคืน key ทั้ง 9 ตัวให้ตรงกับ `solve_thevenin`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: PASS (15 tests)

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/engineering.py bjt_bias/tests/test_engineering.py
git commit -m "feat: add nodal solver and independent cross-check"
```

---

## Task 3: `analyze()` — region, cutoff override, result object

**Files:**
- Modify: `bjt_bias/engineering.py`
- Modify: `bjt_bias/tests/test_engineering.py`

**Interfaces:**
- Consumes: `solve_thevenin`, `solve_nodal`, `cross_check`, `VCE_SAT`
- Produces:
  - `BiasResult` — frozen dataclass, ฟิลด์: `inputs: BiasInputs`, `vbb`, `rb`, `ib`, `ic`, `ie`, `vb`, `ve`, `vc`, `vce` (ทั้งหมด `float`), `region: str` (`"active" | "cutoff" | "saturation"`), `warning: str | None`, `check_passed: bool`, `check_max_rel_diff: float`
  - `analyze(i: BiasInputs) -> BiasResult`

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

```python
from bjt_bias.engineering import analyze

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
```

(import `VCE_SAT` เพิ่มในบรรทัด import เดิม)

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: FAIL — `ImportError: cannot import name 'analyze'`

- [ ] **Step 3: เพิ่ม `BiasResult` และ `analyze()`**

ลำดับที่ต้องเป็น: เรียก `solve_thevenin` และ `solve_nodal` กับ input ดิบ → `cross_check` → ตัดสิน region (`ib <= 0` → cutoff, `vce <= VCE_SAT` → saturation, อื่น ๆ active) → ถ้า cutoff ให้ override `ib/ic/ie/ve/vc/vce` ตาม Global Constraints; ถ้า saturation ใส่ `warning` ภาษาไทย; active ไม่มี warning

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: PASS (19 tests)

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/engineering.py bjt_bias/tests/test_engineering.py
git commit -m "feat: classify BJT region and report bias point"
```

---

## Task 4: Flask app, template, CSS (happy path)

**Files:**
- Create: `bjt_bias/app.py`
- Create: `bjt_bias/templates/index.html`
- Create: `bjt_bias/static/style.css`
- Create: `bjt_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `parse_inputs`, `analyze`, `BiasResult`
- Produces:
  - `create_app() -> Flask`
  - `app` (module-level instance ใน `bjt_bias/app.py`)
  - route: `GET /` และ `POST /`, ฟิลด์ฟอร์ม `vcc, r1, r2, rc, re, beta, vbe`
  - template variables: `form` (`dict[str, str]` ค่าที่กรอก), `result` (`BiasResult | None`), `errors` (`dict[str, str]`)

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

`bjt_bias/tests/test_app.py`:
```python
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
        self.assertIn("7.55488", body)      # VCE
        self.assertIn("Active", body)
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests/test_app.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'bjt_bias.app'`

- [ ] **Step 3: เขียน `app.py`, `index.html`, `style.css`**

`app.py`: `create_app()` สร้าง `Flask(__name__)`, route `/` รับทั้ง GET/POST, POST จะ `request.form.to_dict()` → `parse_inputs` → ถ้ามี error ส่ง `errors` + `form` ไป render, ถ้าผ่าน `analyze` แล้ว render; `app = create_app()`; `if __name__ == "__main__": app.run(debug=True)`

`index.html`: ฟอร์ม 7 ช่องพร้อม label และหน่วย (V, Ω, A) + ตารางผลที่แสดง `IB, IC, IE, VB, VE, VC, VCE` ด้วย `{{ "%.6g"|format(result.ic) }}` + แสดง `result.region` และบรรทัด cross-check ("ตรวจทานอิสระ: ผ่าน" / "ไม่ผ่าน") ห้ามใส่ตัวเลขผลลัพธ์ลงใน HTML ตรง ๆ

`style.css`: จัดกึ่งกลางความกว้าง ~720px, ฟอร์มเป็น grid 2 คอลัมน์, ตารางผลอ่านง่าย — ไม่ต้องมี animation

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: PASS (21 tests)

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/static/style.css bjt_bias/tests/test_app.py
git commit -m "feat: serve BJT bias calculator with Flask"
```

---

## Task 5: Error display and region warning in the UI

**Files:**
- Modify: `bjt_bias/templates/index.html`
- Modify: `bjt_bias/app.py`
- Modify: `bjt_bias/tests/test_app.py`

**Interfaces:**
- Consumes: `errors` dict จาก Task 4, `BiasResult.warning`
- Produces: ไม่มี interface ใหม่ — แค่แสดง `errors[f]` ใต้ฟิลด์นั้น และ `result.warning` ในกล่องเตือน

- [ ] **Step 1: เขียน test ที่ยังไม่ผ่าน**

เพิ่มใน `bjt_bias/tests/test_app.py`:
```python
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
```

- [ ] **Step 2: รัน test ให้เห็นว่า fail**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests/test_app.py -q`
Expected: FAIL — ไม่พบข้อความ error/warning ในหน้า

- [ ] **Step 3: เพิ่มบล็อก error และ warning ใน template**

ใต้ input แต่ละช่อง: `{% if errors.get("vcc") %}<p class="error">{{ errors["vcc"] }}</p>{% endif %}`
เหนือตารางผล: `{% if result.warning %}<p class="warning">{{ result.warning }}</p>{% endif %}`

ถ้อยคำ error ที่ template test ผูกไว้ (ต้องตรง):
- parse ไม่ผ่าน: `"ต้องเป็นตัวเลข"`
- ค่าติดลบ/ศูนย์ของ R: `"ต้องมากกว่าศูนย์"`
- `vbe >= vcc`: `"ต้องน้อยกว่า VCC"`
- warning ของ saturation: `"ไม่ทำงานใน active region"` และ label `"Saturation"`

- [ ] **Step 4: รัน test ให้ผ่าน**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: PASS (26 tests)

- [ ] **Step 5: Commit**

```bash
git add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/tests/test_app.py
git commit -m "feat: show field errors and region warnings"
```

---

## Task 6: README, full verification, merge and push

**Files:**
- Create: `bjt_bias/README.md`
- Modify: ไม่มี

**Interfaces:**
- Consumes: ทั้งหมด
- Produces: ไม่มี

- [ ] **Step 1: เขียน `bjt_bias/README.md`**

ต้องมี: วิธีสร้าง venv, `pip install -r bjt_bias/requirements.txt`, วิธีรัน `.venv\Scripts\python -m bjt_bias.app` แล้วเปิด `http://127.0.0.1:5000`, วิธีรัน test, สมการที่ใช้ 2 วิธี, เกณฑ์ region (`VCE <= 0.2 V` = saturation), และตัวอย่าง input/ผลจาก spec §8

- [ ] **Step 2: รัน test ทั้งหมดและบันทึกผลจริง**

Run: `.venv\Scripts\python -m pytest bjt_bias/tests -q`
Expected: PASS 26 tests — **คัดลอกบรรทัดสรุปจริงมาใส่ในรายงาน ห้ามพิมพ์จากความจำ**

- [ ] **Step 3: ตรวจการแยกชั้น (AC7)**

Run:
```
.venv\Scripts\python -c "import bjt_bias.engineering; print('ok')"
.venv\Scripts\python -c "import ast,sys; t=ast.parse(open('bjt_bias/app.py',encoding='utf-8').read()); print([n.id for n in ast.walk(t) if isinstance(n,ast.ImportFrom)])"
```
Expected: พิมพ์ `ok` และรายการ import ของ `app.py` ไม่มีสูตรคำนวณ (มีแต่ flask, engineering)

- [ ] **Step 4: เดโมจริงบน localhost**

Run: `.venv\Scripts\python -m bjt_bias.app`
จากนั้นเปิด `http://127.0.0.1:5000`, กรอกตัวอย่าง spec §8, ตรวจว่าเห็น `IC = 0.00301746 A`, `VCE = 7.55488 V`, `Active`, `ตรวจทานอิสระ: ผ่าน`
**ปิด server หลังเดโม**

- [ ] **Step 5: Merge และ push**

```bash
git add bjt_bias/README.md docs/superpowers
git commit -m "docs: document BJT bias calculator"
git checkout main
git merge --no-ff feat/bjt-dc-bias -m "merge: BJT DC bias web app"
git push origin main
```
Expected: `git status` แสดง `main...origin/main` และไม่มี commit ค้าง

---

## Self-Review

- **Spec coverage:** §4 (สมการ 2 วิธี) → Task 1, 2; §5 region/cutoff → Task 3, 5; §6 validation → Task 1, 5; §7 ไฟล์/route/format → Task 4; §8 ตัวเลขตัวอย่าง → Task 1, 2, 4; §9 AC1–AC8 → Task 1 (AC1), Task 4/6 (AC2), Task 1/5 (AC3), Task 3 (AC4), Task 2/3 (AC5), Task 6 (AC6, AC7, AC8) — ครบ
- **Step scan:** ทุก step มีคำสั่งหรือ assertion ตรวจได้ ไม่มี "handle edge cases" ลอย ๆ
- **Type consistency:** `BiasInputs` ฟิลด์เดียวกับ `form` key, `cross_check` รับ dict ที่มี key `ic`/`vce` ตรงกับที่ทั้งสอง solver คืน, `BiasResult.ic` ใช้ใน template ตรงชื่อ
- **Review Focus:** ทั้ง 5 ข้อมี test ใน Task 1, 3, 5
- **Proportion:** แผนยาวกว่า spec ประมาณ 2 เท่า เพราะมี test code จริงตามที่ skill กำหนด ไม่ใช่ transcript ของโปรแกรม
