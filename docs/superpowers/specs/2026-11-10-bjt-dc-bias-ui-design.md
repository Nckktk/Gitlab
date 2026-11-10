# Short design — make the BJT bias page match the handout's Lab 2 target screen

Date: 2026-11-10
Status: proposed (awaiting approval)
Builds on: `2026-11-10-bjt-dc-bias-design.md` (approved, shipped at `c59b8a1`)

## Intent and why

The lab handout ships a target screenshot for Lab 2. Its caption in the handout
(the only part of the image this builder can read) names four elements:

> input fields for VCC, R1, R2, RC, RE, beta and VBE; a schematic of the BJT
> Common-Emitter voltage-divider bias circuit; a **DC Bias Results** table; an
> **Operating Region** message.

Our shipped page has the form, the numbers and the region text, but no circuit
schematic, a plain single-column layout, and A/Ω-only units. The handout's
engineering table also asks for `IC [mA]` and warns students to convert kΩ to Ω
before calculating. The goal is a page a grader recognises as the target screen,
without changing the engineering model.

## Goals

- Page reads as the same kind of screen as the handout: header, input card,
  circuit schematic, DC Bias Results, Operating Region badge.
- A resistor unit selector (Ω / kΩ) so the handout's sample values
  (`R1=100`, `R2=22`, `RC=2.2`, `RE=1`) can be typed as printed.
- Currents displayed in engineering units (mA / µA / nA / A) with 6 significant
  figures; voltages stay in V.
- All existing behaviour preserved: validation messages, preserved form values,
  cutoff/saturation overrides, independent cross-check, no JavaScript.

## Non-goals

- No AC, transient, load line, graphs, circuit editor, FET, theme switcher,
  dark mode, export/print feature, localStorage, or front-end framework.
- No unit selector for VCC, VBE, beta (V and dimensionless are unambiguous).
- No change to the engineering model, region thresholds, or cross-check rule.
- No external font/image/CDN asset; the schematic is inline SVG.

## Anti-goals (failure even if it works)

- A page that looks right but silently mis-scales resistance (e.g. treats `100`
  as 100 Ω while the selector says kΩ, or ignores the selector on POST).
- Dropping or weakening any existing validation or the cross-check display.
- Replacing the 6-significant-figure convention with a different precision.

## Approaches for the schematic

| | Approach | Trade-off |
|---|---|---|
| **A (chosen)** | Hand-written inline SVG in `index.html` | Crisp at any zoom, no request, no JS, testable with a substring check; costs ~70 lines of coordinates |
| B | Compose the circuit from `<div>`s and CSS borders | Faster to write; only rectangles, does not read as a schematic |
| C | Ship a raster image the user supplies | Closest to the original art; builder cannot draw it, blurs on zoom, needs a binary in the repo |

A is chosen because the drawing is static, must stay sharp on a projector, and a
missing/broken image link would be a rubric-visible failure.

## Decisions already made (with the human partner)

- Resistor units: dropdown per resistor, Ω or kΩ, converted to Ω before solving.
  Default selection is **kΩ**, because the handout's sample data is in kΩ and the
  caption shows kΩ; the selector is always visible next to each field.
- Currents: displayed in mA/µA/nA with 6 significant figures. IC for the handout
  sample must read `1.22986 mA`.

## How it works

### Input parsing (`bjt_bias/engineering.py`)

- New constants: `RESISTOR_FIELDS = ("r1", "r2", "rc", "re")`,
  `UNIT_OHM = "ohm"`, `UNIT_KOHM = "kohm"`, `UNIT_FACTOR = {ohm: 1.0, kohm: 1e3}`.
- `parse_inputs(raw)` reads `f"{field}_unit"` for each resistor field.
  Missing or empty unit key → Ω (this keeps every existing direct call and test
  valid); an unknown unit string → per-field error `"หน่วยไม่ถูกต้อง"`.
- Order of checks per field: blank → number → finite → apply unit factor →
  `abs(ohms) > MAX_INPUT` → (later) positivity. The `MAX_INPUT` guard therefore
  applies to the converted Ω value.
- `BiasInputs` keeps SI base units (Ω, A, V). No other engineering change.

### Formatting (`bjt_bias/app.py`, view layer)

- `fmt_current(amps)` registered as a Jinja filter:
  `>= 1` → `"%.6g A"`, `>= 1e-3` → mA, `>= 1e-6` → µA, `>= 1e-9` → nA,
  otherwise `"%.6g A"`. Zero prints `0 A`.
- `fmt_voltage(volts)` → `"%.6g V"` (same output as today).
- Engineering module stays free of formatting and Flask.

### Template (`bjt_bias/templates/index.html`)

```
header: BJT DC Bias Calculator        ENG29 2121 · Lab 2
grid:
  left  <section class="card"> Input Parameters
         7 labelled inputs (V, V, kΩ/Ω ×4, –, V, –), inline error per field
         submit button
  right <section class="card"> Circuit
         inline <svg class="schematic" role="img"> with <title>, VCC rail,
         R1 (VCC→base), R2 (base→GND), RC (VCC→collector), Q1 NPN symbol,
         RE (emitter→GND), node dots, and text labels VCC, R1, R2, RC, RE,
         Q1, GND
results <section class="card" id="results"> DC Bias Results
         7 values as label/value pairs: VB, VE, VC, VCE, IC, IE, IB
         Operating Region badge (Active | Cutoff | Saturation) + Thai subtitle
         warning block when present
         existing cross-check line
```

- All section headings are English as in the handout; helper text, errors and
  warnings stay Thai.
- Unit selects keep the submitted selection after POST (server-rendered
  `selected`), like the text inputs keep their values.

### Styling (`bjt_bias/static/style.css`)

- Card-based layout, max-width ~1080px, two columns above 860px, stacked below;
  results full width under the grid.
- Schematic strokes use `currentColor` so it stays legible against the card.
- Region badge palette: green (active), amber (saturation), grey (cutoff), each
  with text, not colour alone.

### Tests (to be written first, TDD)

Engineering:
1. `r1=100` + `r1_unit=kohm` → `inputs.r1 == 100000.0`.
2. Missing `*_unit` keys → treated as Ω (backwards compatible).
3. `r1_unit=mohm` (tampered) → error on `r1`, no exception.
4. `1e10` kΩ (→ 1e13 Ω) → `"ค่ามากเกินไป"`.

Route/template:
5. POST the handout sample with kΩ units → `1.22986 mA`, `8.05216 V`, `Active`.
6. IB renders as `12.2986 µA` for that sample.
7. GET page contains `<svg`, `class="schematic"`, and labels `R1`…`RE`, `Q1`.
8. GET page has four unit selects with `kohm` selected by default.
9. Cutoff input → `Cutoff` badge; saturation input → warning (existing, kept).
10. Existing tests updated where the display convention changed
    (`0.00301746 A` → `3.01746 mA`).

### Docs

- `bjt_bias/README.md`: unit selector + conversion rule, current display units,
  model assumptions (constant β, constant VBE, no Early effect, forward-active
  approximation), notes on the schematic being decorative, and a warning not to
  run Flask's debugger on a public interface.
- This design is referenced from the new plan; the original spec stays as the
  record of the shipped behaviour.

## Constraints

- No new runtime dependency; Flask + pytest only.
- No JavaScript; page must be fully usable with JS disabled.
- `python -m pytest -q` from repo root must stay green.
- Work on a branch, merge to `main`, push; never modify root `electrical.py`,
  `test_electrical.py`, `README.md`.

## Left to the builder

- Exact SVG coordinates and stroke widths; final CSS palette, spacing, breakpoint.
- Thai helper wording and the exact region subtitle text.
- Whether the region badge shows the raw VCE next to the label (optional).
