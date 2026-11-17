# Lab 03 Three-Mode BJT Bias Web App Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the shipped Lab 2 Flask app in place so one page selects Fixed, Emitter or Voltage Divider BJT bias, with per-mode equations in Python, per-mode validation, preserved Divider output, Playwright MCP config and an honest A1-A5 browser validation record.

**Architecture:** `engineering.py` stays Flask-free; add mode constants, mode-specific input dataclasses, a shared field parser, three solvers and one `analyze_mode()` dispatcher. `app.py` reads `mode`/`change_mode`, dispatches, and passes presentation metadata to the existing Jinja template. The form switches mode by POST reload (no JavaScript) and shows only the fields/schematic for the chosen mode.

**Tech Stack:** Python 3.12, Flask 3, pytest 8 (existing tests only), Jinja templates, inline SVG, CSS, Playwright MCP (config only).

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-bjt-bias-multi-mode-design.md`

## Global Constraints

- Extend `bjt_bias/` in place; do not create a new project or move equations into HTML/JS.
- `engineering.py` must never import Flask.
- Divider must keep `IC = 1.22986 mA`, `VCE = 8.05216 V` for `VCC=12, R1=100 kΩ, R2=22 kΩ, RC=2.2 kΩ, RE=1 kΩ, β=100, VBE=0.70`.
- Existing tests in `bjt_bias/tests/` must remain unchanged and all pass; do not add new unittest files.
- Keep existing keys/attributes (`vb`, `ve`, `vc`, `vce`, `ic`, `ie`, `ib`, `region`, `warning`, `check_passed`, `check_max_rel_diff`) and `%.6g` formatting.
- Resistors accept Ω or kΩ, converted to Ω **once** during parsing; missing `*_unit` means Ω.
- Unknown mode must produce an error, never fall back to Divider.
- Invalid/missing/non-finite/non-positive input → error, no result. Valid input with `IB <= 0` or `VCE <= 0.2 V` → model-limit warning, no invented cutoff/saturation values for new modes.
- Divider keeps its existing cutoff/saturation reporting and two-solver cross-check.
- No JavaScript, no SPICE/AC/load line, no Playwright entry in `requirements.txt`.
- Do not install Node.js or system tools without permission. If a real browser cannot be run, report `NOT RUN` with the actual blocker; never fabricate browser evidence.
- Python commands use `.venv\Scripts\python.exe` from the repository root; set `$env:PYTHONIOENCODING='utf-8'` when printing Thai/µ.

## Review Focus

- `mode=unknown` → error on the page, no result block, no silent Divider fallback → Task 2 test: POST `mode=bogus` asserts error text and asserts `DC Bias Results` absent.
- `mode=fixed` with `rb=0` → field error, no result, page still 200 → Task 2 test: POST asserts `มากกว่าศูนย์` and result absent.
- `mode=emitter` with `re` omitted or blank → error only for `re`, no error for `r1`/`r2` → Task 2 test: POST asserts `re` error and no `r1` error text.
- Stale result after a rejected submission → no result block rendered at all → Task 2 test: first POST valid then POST `rb=0`, assert result heading absent in second response.
- Unit scaling for new `rb` (`1 MΩ = 1000 kΩ = 1e6 Ω`) applied exactly once → Task 1 check: `parse_mode_inputs` with `rb=1000, rb_unit=kohm` yields `rb == 1e6`; Task 2 POST with `rb=1000, rb_unit=kohm` yields A2 expected values.

## File Structure

| File | Responsibility |
|---|---|
| `bjt_bias/engineering.py` | Mode constants, mode input dataclasses, shared parser, three solvers, `analyze_mode()` |
| `bjt_bias/app.py` | Route, mode dispatch, `change_mode` path, presentation metadata |
| `bjt_bias/templates/index.html` | Mode bar, per-mode fields, per-mode schematic, labelled results |
| `bjt_bias/static/style.css` | Mode bar + model-limit badge styling |
| `README.md`, `bjt_bias/README.md` | Run/usage notes for three modes |
| `docs/validation.md` | A1-A5 table, independent references, method/status/evidence |
| `opencode.json` | Playwright MCP server config (V2 shape) |

---

### Task 1: Mode-aware engineering core

**Files:**
- Modify: `bjt_bias/engineering.py`
- Test: one-off verification command (no new test files)

**Interfaces:**
- Consumes: existing `parse_inputs`, `solve_thevenin`, `cross_check`, `BiasResult`, constants in `engineering.py`.
- Produces: `MODE_DIVIDER='divider'`, `MODE_FIXED='fixed'`, `MODE_EMITTER='emitter'`, `MODES`, `MODE_FIXED_FIELDS`, `MODE_EMITTER_FIELDS`, `FixedInputs(vcc, rb, rc, beta, vbe)`, `EmitterInputs(vcc, rb, rc, re, beta, vbe)`, `parse_mode_inputs(raw, mode) -> (object | None, dict[str, str])`, `analyze_fixed(i) -> BiasResult`, `analyze_emitter(i) -> BiasResult`, `analyze_mode(mode, raw) -> (BiasResult | None, dict[str, str])`.

- [ ] **Step 1: Add mode constants and input dataclasses**

In `bjt_bias/engineering.py`, add the three mode constants and `MODES`, add `MODE_ERROR = "โหมดไม่ถูกต้อง"`, add field tuples `("vcc", "rb", "rc", "beta", "vbe")` and `("vcc", "rb", "rc", "re", "beta", "vbe")`, and define frozen dataclasses `FixedInputs` and `EmitterInputs`. Extend the `BiasResult.inputs` annotation to the three-type union. Do not change `FIELDS`, `RESISTOR_FIELDS` or any existing function signature.

- [ ] **Step 2: Factor the shared field parser**

Extract the body of `parse_inputs` (number/finite/limit/positive checks and `UNIT_FACTORS` scaling) into `_parse_fields(raw, fields) -> (dict[str, float], dict[str, str])`. `parse_inputs` must call `_parse_fields(raw, FIELDS)` and keep returning `BiasInputs(**values)`; keep `vbe < vcc` and `vbe >= 0` checks where they are. Resistors are any field in `ALL_RESISTOR_FIELDS = ("r1", "r2", "rb", "rc", "re")`.

- [ ] **Step 3: Implement `parse_mode_inputs`**

Signature `parse_mode_inputs(raw: dict[str, str], mode: str) -> tuple[BiasInputs | FixedInputs | EmitterInputs | None, dict[str, str]]`. Divider delegates to `parse_inputs`; Fixed/Emitter call `_parse_fields` with their field tuple and construct their dataclass. Unknown mode returns `(None, {"mode": MODE_ERROR})`. Validate only the selected mode's fields.

- [ ] **Step 4: Implement the two new solvers and `analyze_mode`**

`analyze_fixed` uses `IB=(VCC−VBE)/RB`, `VE=0`, `VB=VBE`; `analyze_emitter` uses `IB=(VCC−VBE)/(RB+(β+1)RE)`, `VE=IE·RE`; both use `IC=βIB`, `IE=(β+1)IB`, `VC=VCC−ICRC`, `VCE=VC−VE`. When `IB <= 0` or `VCE <= 0.2`, set `region='model-limit'` and a Thai warning saying the Forward Active model may not apply and values are from the linear equations; otherwise `region='active'`, `warning=None`. Set `check_passed=True`, `check_max_rel_diff=0.0` (template hides the cross-check line for non-divider modes). `analyze_mode` dispatches to unchanged `analyze()` for Divider.

- [ ] **Step 5: Run existing tests and independent checks**

Run:
```powershell
.\.venv\Scripts\python.exe -m pytest bjt_bias\tests -q
$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -c "from bjt_bias.engineering import *; a,e=parse_mode_inputs({'vcc':'12','rb':'1000','rb_unit':'kohm','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}, MODE_FIXED); assert not e and a.rb==1e6; r,_=analyze_mode(MODE_FIXED, {'vcc':'12','rb':'1000','rb_unit':'kohm','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}); assert abs(r.ic-1.13e-3)<1e-9 and abs(r.vce-9.514)<1e-9; r2,_=analyze_mode(MODE_EMITTER, {'vcc':'12','rb':'1000','rb_unit':'kohm','rc':'2.2','rc_unit':'kohm','re':'1','re_unit':'kohm','beta':'100','vbe':'0.7'}); assert abs(r2.ic-1.02633969e-3)<1e-9 and abs(r2.vce-8.70545)<1e-4; r3,e3=analyze_mode('bogus', {}); assert r3 is None and 'mode' in e3; print('engineering OK')"
```
Expected: all existing tests pass; command prints `engineering OK`.

- [ ] **Step 6: Commit**

```powershell
git add bjt_bias/engineering.py
git commit -m "feat(lab3): add mode-aware bias solvers and validation"
```

---

### Task 2: Flask route and three-mode form

**Files:**
- Modify: `bjt_bias/app.py`
- Modify: `bjt_bias/templates/index.html`
- Modify: `bjt_bias/static/style.css`
- Test: one-off Flask test-client verification command (no new test files)

**Interfaces:**
- Consumes: `MODES`, `MODE_*`, `analyze_mode`, `ALL_RESISTOR_FIELDS` from Task 1.
- Produces: `index()` accepting `mode` and `change_mode` form keys; template variables `mode`, `mode_label`, `fields`, `form`, `errors`, `result`.

- [ ] **Step 1: Update `app.py` route and unit normalisation**

Make `normalize_units` loop over `ALL_RESISTOR_FIELDS`. Add `MODE_FIELDS_META` mapping each mode to the exact `(name, label, kind)` tuples for the form (`vcc`/`vbe` kind V, `beta` kind β, resistors kind `resistor`: Divider `r1,r2,rc,re`; Fixed `rb,rc`; Emitter `rb,rc,re`). In `index()`: on GET use `mode=MODE_DIVIDER`, empty form; on POST take `mode` from the form, and if `change_mode` is present re-render form-only with preserved values, `errors={}`, `result=None`; otherwise call `analyze_mode(mode, form)`. Pass `mode`, `mode_label`, `fields=MODE_FIELDS_META.get(mode, MODE_FIELDS_META[MODE_DIVIDER])`, and the results. Existing `fmt_current`, `fmt_voltage` and template filters stay unchanged.

- [ ] **Step 2: Update the template**

Replace the hard-coded field list with `{% for name, label, kind in fields %}` while keeping the existing `<label for>`, `*_unit` select and error paragraph structure. Add a mode bar above the fields: `<select id="mode" name="mode">` with values from `MODES` order and labels `Voltage Divider Bias`, `Fixed Bias`, `Emitter Bias`, plus `<button type="submit" name="change_mode" value="1">เปลี่ยนโหมด</button>`; show `errors.get('mode')` there. Replace the single schematic with three sibling inline SVGs selected by `mode`, each `class="schematic"`: Divider keeps the current R1/R2/RC/RE drawing unchanged; Fixed shows RB from VCC to base, emitter direct to ground, RC, Q1, VCC, GND; Emitter shows RB, RC, RE, Q1, VCC, GND. In results, show the mode label in the heading, add `model-limit` to `region_thai`, and render the `ตรวจทานอิสระ` line only when `mode == 'divider'`.

- [ ] **Step 3: Add minimal CSS**

Add `.mode-bar` (flex, wrap, gap, bottom border), `.mode-bar button` compact/secondary styling, and `.region-model-limit` badge colours. Do not restyle existing cards.

- [ ] **Step 4: Run existing tests and route checks**

Run:
```powershell
.\.venv\Scripts\python.exe -m pytest bjt_bias\tests -q
$env:PYTHONIOENCODING='utf-8'; .\.venv\Scripts\python.exe -c "
from bjt_bias.app import create_app
c=create_app().test_client()
base={'vcc':'12','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}
def post(**kw): return c.post('/',data={**base,**kw}).get_data(as_text=True)
a1=post(mode='divider',r1='100',r1_unit='kohm',r2='22',r2_unit='kohm',re='1',re_unit='kohm')
assert '1.22986 mA' in a1 and '8.05216 V' in a1
a2=post(mode='fixed',rb='1000',rb_unit='kohm')
assert '1.13 mA' in a2 and '9.514 V' in a2 and 'Fixed Bias' in a2
a3=post(mode='emitter',rb='1000',rb_unit='kohm',re='1',re_unit='kohm')
assert '1.02634 mA' in a3 and '8.70545 V' in a3
a4=post(mode='emitter',rb='1000',rb_unit='kohm',re='2',re_unit='kohm')
assert '940.1 µA' in a4 and '8.03278 V' in a4
missing=post(mode='emitter',rb='1000',rb_unit='kohm')
assert missing.count('class="error"')==1 and 'name="r1"' not in missing
c.post('/',data={**base,'mode':'fixed','rb':'1000','rb_unit':'kohm'})
bad=post(mode='fixed',rb='0')
assert 'มากกว่าศูนย์' in bad and 'DC Bias Results' not in bad
unknown=post(mode='bogus',rb='1000',rb_unit='kohm')
assert 'โหมดไม่ถูกต้อง' in unknown and 'DC Bias Results' not in unknown
reset=post(mode='fixed',rb='0',change_mode='1')
assert 'DC Bias Results' not in reset
print('routes OK')"
```
Expected: existing tests pass; command prints `routes OK`.

- [ ] **Step 5: Commit**

```powershell
git add bjt_bias/app.py bjt_bias/templates/index.html bjt_bias/static/style.css
git commit -m "feat(lab3): selectable bias mode in the web form"
```

---

### Task 3: Documentation, validation table and MCP config

**Files:**
- Modify: `README.md`, `bjt_bias/README.md`
- Create: `docs/validation.md`, `opencode.json`
- Test: file review + JSON parse command

**Interfaces:**
- Consumes: expected values in Task 1/2 verification and the design doc.
- Produces: runnable instructions, A1-A5 table, Playwright MCP config.

- [ ] **Step 1: Update both READMEs**

Document the new `mode` field, the three formulas, the `เปลี่ยนโหมด` button, `rb` unit selector, and that Divider output is unchanged. Keep the existing run/test commands working. Do not add Playwright to `requirements.txt`.

- [ ] **Step 2: Create `docs/validation.md`**

Include: shared inputs `VCC=12 V, RC=2.2 kΩ, β=100, VBE=0.70 V`; tolerance `0.01 mA` / `0.02 V`; the independent reference values `A1 IC 1.22986 mA, VCE 8.05216 V`, `A2 1.13000 mA, 9.51400 V`, `A3 1.02634 mA, 8.70545 V`, `A4 0.94010 mA (940.1 µA), 8.03278 V` with the equation used; A5 expectation (error for `RB=0`, no stale result). Columns: ID | method | inputs | expected | observed (with unit) | status | evidence. Until a real browser case runs, set method/status to `NOT RUN` with the exact blocker and leave observed/evidence as `—`; state the fallback checks that were actually run. Add the A3→A4 direction prediction (IC decreases when RE increases) and the closing question's data path.

- [ ] **Step 3: Create `opencode.json` with the V2 Playwright config**

Use exactly `{"mcp":{"servers":{"playwright":{"type":"local","command":["npx","-y","@playwright/mcp@latest","--browser","chrome","--isolated"]}}}}`. If a root `opencode.json` already exists, merge only the `mcp.servers.playwright` entry instead of overwriting.

- [ ] **Step 4: Verify files**

Run:
```powershell
python -m json.tool opencode.json
git diff --check
```
Expected: valid JSON; no whitespace errors.

- [ ] **Step 5: Commit**

```powershell
git add README.md bjt_bias/README.md docs/validation.md opencode.json
git commit -m "docs(lab3): three-mode guide, A1-A5 table and MCP config"
```

---

### Task 4: Browser verification attempt and delivery

**Files:**
- Modify: `docs/validation.md` (observations/status/evidence only)

**Interfaces:**
- Consumes: running Flask app, `docs/validation.md`, config from Task 3.
- Produces: truthful browser status, final test evidence, commit; no source changes unless a real failure is found.

- [ ] **Step 1: Start Flask and confirm HTTP**

Run in the background from repo root:
```powershell
.\.venv\Scripts\python.exe -m flask --app bjt_bias.app run
```
Confirm `http://127.0.0.1:5000/` returns 200 via `Invoke-WebRequest`. Keep the server running.

- [ ] **Step 2: Attempt a real browser case**

Check whether a browser tool or Playwright MCP is available in this session. This environment has Chrome and Edge installed but no `node`/`npx` on PATH and no browser tool. If a browser tool is available, navigate, `browser_snapshot`, select mode, fill fields, submit, read the actual result text and capture one screenshot for A2. Otherwise, try a dev-only install inside the existing venv (do not add to `requirements.txt`, do not install Node):
```powershell
.\.venv\Scripts\python.exe -m pip install playwright
```
If install and Chrome launch succeed, run a short throwaway Python Playwright script that performs A1-A5 through the real page, writes observed values into `docs/validation.md` and saves one screenshot under `docs/`. If any step fails, stop and record `NOT RUN` with the exact error text; do not use `curl`, source-code reading or the Flask test client as a substitute for a browser PASS.

- [ ] **Step 3: Re-run the full existing suite and record the result**

```powershell
.\.venv\Scripts\python.exe -m pytest bjt_bias\tests -q
```
Expected: all tests pass. Paste the summary line into `docs/validation.md` under a clearly labelled "non-browser regression check" heading.

- [ ] **Step 4: Review the staged diff before delivery**

```powershell
git status --short
git diff
git add -A
git diff --staged
```
Confirm no `.venv`, `.env`, credentials, screenshots of private data or unintended files are staged. If a real failure was found and fixed, re-run Task 2 step 4 and this step.

- [ ] **Step 5: Commit the validation record**

```powershell
git commit -m "docs(lab3): record browser acceptance results"
```
Report the GitHub-ready commit SHA, the exact browser method/status, and any remaining `NOT RUN` cases. Do not push until the user explicitly confirms pushing.
