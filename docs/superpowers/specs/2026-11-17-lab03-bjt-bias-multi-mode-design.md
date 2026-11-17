# Short design — Lab 03: one Flask web app, three BJT bias circuits

Date: 2026-11-17
Status: approved by human partner 2026-11-17
Builds on: `2026-11-10-bjt-dc-bias-ui-design.md` (Lab 2, shipped at `e5ab2cf`)

## Intent and why

The Lab 03 handout (`ENG29_2121_Lab03_BJT_Bias_Web_App.html`) asks us to extend the
shipped Lab 2 Flask app in place: keep Voltage Divider Bias producing exactly the
same numbers, add Fixed Bias and single-supply Emitter Bias, select the circuit
from the form, validate only the fields the selected circuit needs, and verify the
rendered page through a browser using a student-provided reference table (A1-A5).
The work is assessed on preserving the old result, clean separation of equations
in Python, honest browser evidence and reproducible delivery.

## Goals

- Three selectable modes: `divider` (default, unchanged), `fixed`, `emitter`.
- Per-mode functions in `engineering.py` returning the same result shape; no
  equations in templates or JavaScript.
- Per-mode field validation in Flask/Python, including unknown-mode rejection,
  with Thai error messages consistent with Lab 2.
- Form shows only the relevant fields for the selected mode, with a no-JavaScript
  mode switch that reloads the form and preserves entered values.
- Results show the selected mode and never display a previous run's numbers for a
  rejected submission.
- Add Playwright MCP config and a filled A1-A5 validation table with independent
  reference values; keep existing tests unchanged and runnable.

## Non-goals

- No SPICE, AC/transient, load line, bypass caps, unittest additions, new app,
  front-end framework, or JavaScript mode switching.
- No install of Node.js / Playwright binaries without permission.
- No change to Lab 2's 6-significant-figure formatting, unit selectors, region
  thresholds, cross-check display, or Divider equations.
- No fabricating browser evidence when no browser tool is available.

## Anti-goals (failure even if it works)

- Divider output drifting from `IC 1.22986 mA / VCE 8.05216 V` for the handout
  case, or existing tests breaking.
- Silently defaulting an unknown mode to Divider, or applying kΩ scaling twice.
- Showing a stale result block after validation errors.
- Reporting a browser PASS without having run a real browser case.

## Constraints and decisions already made

- Extend the current `bjt_bias/` package; keep `engineering.py` free of Flask.
- Reuse the existing result attribute names (`vb`, `ve`, `vc`, `vce`, `ic`, `ie`,
  `ib`, `region`, `warning`, `check_passed`, `check_max_rel_diff`) because the
  handout explicitly permits Lab 2's existing key names.
- Preserve `parse_inputs(raw)` and `analyze(i)` signatures for Divider so all
  existing tests pass; add mode-aware wrappers rather than rewriting them.
- Keep ohm/kΩ selectors and the "missing unit key means ohm" rule; `rb` joins
  `RESISTOR_FIELDS` as a resistor with a unit selector.
- Mode switching via POST with a `change_mode` flag; no JavaScript.
- Browser step: add `opencode.json` Playwright MCP config (V2 shape). If no
  browser tool / node is available in the execution environment, record `NOT RUN`
  with the real reason, verify behaviour with Flask's test client as a fallback,
  and state the method honestly. Do not install system tools unprompted.

## Approaches considered

| Approach | Trade-off | Outcome |
|---|---|---|
| A. Extend `bjt_bias/` in place, add mode wrappers around existing pure functions | Keeps all validated Lab 2 behaviour and tests; small, reviewable diff | **Chosen** |
| B. Create a separate Lab 3 project | Violates the handout's "do not build a new system" rule | Rejected |
| C. Move the equations into the Jinja template / client JS | Equations become unverifiable, breaks pure-module rule | Rejected |

## Engineering model

Common inputs: `VCC, RC, beta, VBE` (V, Ω, dimensionless, V). Resistor fields
accept Ω or kΩ and are converted to Ω once during parsing.

| Mode | Extra inputs | IB |
|---|---|---|
| Fixed | `RB` | `(VCC - VBE) / RB` |
| Emitter | `RB, RE` | `(VCC - VBE) / (RB + (beta + 1) * RE)` |
| Divider | `R1, R2, RE` | `(VTH - VBE) / (RTH + (beta + 1) * RE)` |

`VTH = VCC*R2/(R1+R2)`, `RTH = R1*R2/(R1+R2)`;
`IC = beta*IB`, `IE = (beta+1)*IB`, `VE = IE*RE` (Fixed: `VE = 0`),
`VB = VE + VBE`, `VC = VCC - IC*RC`, `VCE = VC - VE`.

Invalid/missing/non-finite/non-positive input → per-field error and no result.
Valid input with `IB <= 0` or `VCE <= 0.2 V` → warning that the Forward Active
model may not apply; no cutoff/saturation values invented for the new modes.
Divider keeps its existing cutoff/saturation reporting unchanged.

## File-level shape of the change

1. `bjt_bias/engineering.py` — add `MODE_*` constants, `FixedInputs` /
   `EmitterInputs`, mode-aware `parse_mode_inputs(raw)`, `analyze_fixed`,
   `analyze_emitter`, and a shared result builder; leave existing Divider
   functions and tests intact.
2. `bjt_bias/app.py` — read `mode` and `change_mode`, dispatch to the right
   solver, pass `mode` and per-mode field metadata to the template, render no
   result on errors.
3. `bjt_bias/templates/index.html` — mode select + "เปลี่ยนโหมด" button, render
   only relevant fields, per-mode schematic, results labelled with the mode.
4. `bjt_bias/static/style.css` — minimal styles for the mode bar/schematic.
5. `README.md`, `bjt_bias/README.md` — three-mode run/usage notes and formulas.
6. `docs/validation.md` — A1-A5 table with inputs, independent expectations,
   observed values, method, status and evidence placeholders.
7. `opencode.json` — Playwright MCP server config (V2 shape), merged if a config
   already exists at project root.

## What is left to the builder

Follow the plan produced by `writing-plans`; run the existing test suite and the
independent A1-A5 reference checks before claiming completion. Report browser
status truthfully.
