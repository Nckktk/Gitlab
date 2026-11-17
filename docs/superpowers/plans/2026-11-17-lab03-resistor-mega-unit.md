# Lab 03 MΩ Resistor Unit + Fixed Bias Verification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let every resistor field use `Ω`, `kΩ` or `MΩ` from one shared table, and prove with independent numbers and a real browser that Fixed bias is correct.

**Architecture:** `bjt_bias/engineering.py` owns the unit factors and an ordered `(value, label)` list; `app.py` passes that list to the Jinja template, which renders the dropdown by looping instead of hardcoding two `<option>` tags. Parsing keeps the existing single-scaling rule.

**Tech Stack:** Python 3.12, Flask 3, Jinja templates, existing 43 pytest tests, throwaway Playwright/Chrome script inside the worktree `.venv`.

**Spec:** `docs/superpowers/specs/2026-11-17-lab03-resistor-mega-unit-design.md`

## Global Constraints

- Resistor units are exactly `Ω` (`ohm`, ×1), `kΩ` (`kohm`, ×1e3) and `MΩ` (internal key `megaohm`, ×1e6). No mΩ, GΩ or TΩ. `mohm` stays unknown because an existing test uses it as the invalid-unit example.
- The dropdown default stays `kΩ`; a POST with a missing `*_unit` key still means `Ω` (Lab 2 compatibility).
- Scale once, during parsing. `1 megaohm` and `1000 kohm` must both equal `1e6 Ω` and give identical results.
- Divider equations, region rules, `MAX_INPUT = 1e12`, and all A1–A5 expected values stay unchanged.
- Unknown unit still produces `หน่วยไม่ถูกต้อง`; no new error text.
- No new unittest files and no JavaScript. Throwaway scripts live under `.superpowers/sdd/` and are gitignored.
- Python commands use `C:\Users\b6648794\Desktop\Gitlab\.venv\Scripts\python.exe` with `$env:PYTHONIOENCODING='utf-8'`; Playwright scripts use the worktree `.venv`.
- Flask is already running at `http://127.0.0.1:5000/`; reuse it, do not start a second server.

## Review Focus

- `rb=1, rb_unit=megaohm` → parsed `rb == 1e6`, results `IC 1.13 mA / VCE 9.514 V` — Task 1 one-off assertion.
- `rb=1000, rb_unit=kohm` → still `1e6`, no second multiplication — Task 1 one-off assertion.
- Missing `rb_unit` → `1e6/1000 = 1000 Ω` behaviour unchanged, no silent new default — Task 1 existing pytest + assertion.
- `rb_unit=bogus` → `หน่วยไม่ถูกต้อง`, no result — Task 1 one-off assertion.
- GET page and `เปลี่ยนโหมด` POST show `kΩ` selected by default — Task 1 route assertion.
- Fixed bias hand calculation for A2 (`1 MΩ`) and at least two other RB values matches the page, including the `model-limit` case — Task 2 independent check + browser.

---

### Task 1: One unit table drives parsing and the dropdown

**Files:**
- Modify: `bjt_bias/engineering.py` (unit constants and factors near lines 14–16)
- Modify: `bjt_bias/app.py` (template variables near `index()`)
- Modify: `bjt_bias/templates/index.html` (resistor `<select>` near lines 41–46)
- Test: one-off assertion commands (no new test files)

**Interfaces:**
- Consumes: existing `UNIT_FACTORS`, `UNIT_OHM`, `UNIT_KOHM`, `_parse_fields`, `parse_mode_inputs`, `analyze_mode`.
- Produces: `UNIT_MOHM = "megaohm"` (the draft's `mohm` is taken by an existing negative test), `UNIT_FACTORS` with `megaohm: 1e6`, `RESISTOR_UNITS = ((UNIT_OHM, "Ω"), (UNIT_KOHM, "kΩ"), (UNIT_MOHM, "MΩ"))`; template variables `resistor_units` and `default_resistor_unit = "kohm"`.

- [ ] **Step 1: RED — run the new unit assertions against current code**

Run with `$env:PYTHONIOENCODING='utf-8'`:

```powershell
& 'C:\Users\b6648794\Desktop\Gitlab\.venv\Scripts\python.exe' -c "from bjt_bias.engineering import parse_mode_inputs, analyze_mode, MODE_FIXED; i,e=parse_mode_inputs({'vcc':'12','rb':'1','rb_unit':'megaohm','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}, MODE_FIXED); assert not e and i.rb==1e6; r,_=analyze_mode(MODE_FIXED, {'vcc':'12','rb':'1','rb_unit':'megaohm','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}); assert abs(r.vc-9.514)<1e-9; print('megaohm OK')"
```

Expected: FAIL with `assert not e` because `megaohm` is not in `UNIT_FACTORS` yet (`errors['rb'] == 'หน่วยไม่ถูกต้อง'`).

- [ ] **Step 2: Add the MΩ constant and presentation list in `engineering.py`**

Define `UNIT_MOHM = "megaohm"`, extend `UNIT_FACTORS` with `UNIT_MOHM: 1e6`, and define `RESISTOR_UNITS` as the ordered tuple of `(unit value, label)` pairs listed in Interfaces. Do not change `_parse_fields` — its `UNIT_FACTORS` lookup already handles any new key.

- [ ] **Step 3: Pass the unit list into the template from `app.py`**

Import `RESISTOR_UNITS` and `UNIT_KOHM`; add `resistor_units=RESISTOR_UNITS` and `default_resistor_unit=UNIT_KOHM` to every `render_template("index.html", ...)` call (GET, calculate POST, `change_mode` POST).

- [ ] **Step 4: Replace the hardcoded options in `index.html`**

Keep `{% set unit = form.get(name ~ "_unit") or default_resistor_unit %}` and the existing `<select>` attributes; replace the two `<option>` lines with one loop over `resistor_units` that emits `value="{{ value }}"` and `{{ label }}`, with `selected` when `unit == value`.

- [ ] **Step 5: GREEN — rerun assertions and existing suite**

Run the Step 1 command again, plus:

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONPATH=(Get-Location).Path; & 'C:\Users\b6648794\Desktop\Gitlab\.venv\Scripts\python.exe' -c "from bjt_bias.app import create_app; from bjt_bias.engineering import parse_mode_inputs, MODE_FIXED; c=create_app().test_client(); d={'vcc':'12','rb':'1','rb_unit':'megaohm','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7','mode':'fixed'}; b=c.post('/',data=d).get_data(as_text=True); assert '9.514 V' in b and 'MΩ' in b; g=c.get('/').get_data(as_text=True); assert g.count('value=\"kohm\" selected')==4 and 'value=\"megaohm\" selected' not in g; i,e=parse_mode_inputs({'vcc':'12','rb':'1000','rb_unit':'kohm','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}, MODE_FIXED); assert not e and i.rb==1e6; _,e2=parse_mode_inputs({'vcc':'12','rb':'1','rb_unit':'bogus','rc':'2.2','rc_unit':'kohm','beta':'100','vbe':'0.7'}, MODE_FIXED); assert e2['rb']=='หน่วยไม่ถูกต้อง'; print('units OK')"
```

```powershell
& 'C:\Users\b6648794\Desktop\Gitlab\.venv\Scripts\python.exe' -m pytest bjt_bias\tests -q
```

Expected: `megaohm OK`, `units OK`, `43 passed`.

- [ ] **Step 6: Commit**

```powershell
git add bjt_bias/engineering.py bjt_bias/app.py bjt_bias/templates/index.html
git commit -m "feat(lab3): add megaohm resistor unit"
```

---

### Task 2: Independent Fixed-bias verification and docs

**Files:**
- Modify: `README.md`, `bjt_bias/README.md`, `docs/validation.md`
- Test: throwaway independent calculation + existing Playwright script (no new committed tests)

**Interfaces:**
- Consumes: the fixed solver from Task 1, `docs/validation.md` table, `.superpowers/sdd/2026-11-17-lab03-bjt-bias-multi-mode/browser_check.py`.
- Produces: documented A2 `1 MΩ` case, an independent Fixed verification table with numbers calculated outside the app, and browser evidence.

- [ ] **Step 1: Compute independent reference numbers**

Using a Python expression that does **not** import `bjt_bias` (plain arithmetic only), compute for `VCC=12, RC=2200, β=100, VBE=0.7` with `RB ∈ {1e6, 470e3, 100e3}`: `IB=(VCC−VBE)/RB`, `IC=β·IB`, `VE=0`, `VC=VCC−IC·RC`, `VCE=VC`. Record all five values at full precision. Expected A2 `IC=0.00113 A`, `VC=VCE=9.514 V`; `RB=100 kΩ` must give negative `VC` and therefore a `model-limit` warning.

- [ ] **Step 2: Confirm the page matches those references**

For each case, POST through Flask or use the existing browser script and assert the rendered `IC`/`VC`/`VCE` match Step 1 to 6 significant figures. Expected: all three match; `RB=100 kΩ` shows the `model-limit` badge and warning, not a fake cutoff/saturation value.

- [ ] **Step 3: Add the MΩ case to the throwaway browser script and run it**

In `.superpowers/sdd/2026-11-17-lab03-bjt-bias-multi-mode/browser_check.py`, add a case `A2-megaohm`: mode `fixed`, `rb=1`, `rb_unit=megaohm`, all other fields as A2. Restart the Flask server after code changes (plain `flask run` has no auto-reload), then run the script. Expected: `A2-megaohm` shows `VC 9.514 V`, `VCE 9.514 V`, `IC 1.13 mA`, `errors: []`, `has_result: true`; original A1–A5 unchanged.

- [ ] **Step 4: Write the documentation**

In both READMEs, add `MΩ` to the resistor unit line and show `A2 = RB 1 MΩ` as equivalent to `1000 kΩ`. In `docs/validation.md`, add the `A2-megaohm` row to the A1–A5 table (same expected/observed values) and a clearly labelled **Fixed bias independent verification** section containing the Step 1 table, the Step 2 verdict with actual numbers, and the browser method used.

- [ ] **Step 5: Verify and commit**

```powershell
& 'C:\Users\b6648794\Desktop\Gitlab\.venv\Scripts\python.exe' -m pytest bjt_bias\tests -q
git diff --check
git status --short
git add README.md bjt_bias/README.md docs/validation.md docs/superpowers/specs/2026-11-17-lab03-resistor-mega-unit-design.md docs/superpowers/plans/2026-11-17-lab03-resistor-mega-unit.md
git commit -m "docs(lab3): verify fixed bias and document megaohm unit"
```

Expected: `43 passed`, no whitespace errors, no `.venv`/scratch files staged.
