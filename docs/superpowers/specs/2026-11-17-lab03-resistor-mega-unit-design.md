# Short design — add MΩ resistor unit + verify Fixed bias

Date: 2026-11-17
Status: approved by human partner 2026-11-17

## Intent and why

The partner hit `VC = -2474 V` in A2 because `RB` was submitted as `1000 Ω`
instead of `1000 kΩ`. Adding an explicit **MΩ** choice lets them enter `1 MΩ`
directly and removes that trap. They also asked to verify that Fixed bias really
calculates correctly, since the odd output made them doubt the mode.

## Goals

- Resistor dropdowns offer exactly `Ω`, `kΩ`, `MΩ` (no mΩ/GΩ).
- `1 MΩ` parses to `1e6 Ω` once, producing the same A2 result as `1000 kΩ`.
- Dropdown options come from one table in `engineering.py`; no duplicated
  `<option>` markup in the template.
- Independent verification that Fixed bias is correct: hand calculation,
  one-off assertion, and a real-browser case recorded in `docs/validation.md`.
- Existing 43 tests and A1–A5 expected values stay unchanged.

## Non-goals / anti-goals

- No mΩ, GΩ, TΩ, free-text prefix parsing, or JavaScript.
- No change to Divider equations, region rules, or `MAX_INPUT`.
- Default dropdown stays `kΩ`; a missing `*_unit` key still means `Ω` so Lab 2
  form posts keep working.
- A2 must remain `IC 1.13 mA / VC 9.514 V / VCE 9.514 V` for every equivalent
  unit spelling. Double-scaling or a silent fallback would be a failure.

## Decisions already made

- **Chosen approach:** add `UNIT_MOHM` with factor `1e6` to `UNIT_FACTORS`, add
  an ordered `(value, label)` list for the dropdown, pass it from `app.py` into
  the template and loop over it. One definition drives both parsing and
  rendering. The internal key is `megaohm` (not `mohm`) because the existing
  test `test_engineering.py:84` deliberately uses `mohm` as an unknown-unit
  example and existing tests must not change; the visible label is `MΩ`.
- Rejected: hard-code a third `<option>` in `index.html` only (two sources of
  truth; label and factor could drift). Rejected: replace the select with a
  text field that accepts `1M` (breaks existing form posts/tests and is more
  machinery than the request needs).
- `MAX_INPUT = 1e12` is unaffected: `1000 MΩ = 1e9 Ω`.
- Unknown unit still produces `หน่วยไม่ถูกต้อง`; no new error text needed.

## File-level shape

1. `bjt_bias/engineering.py` — add `UNIT_MOHM`, extend `UNIT_FACTORS`, add
   `RESISTOR_UNITS = ((UNIT_OHM, "Ω"), (UNIT_KOHM, "kΩ"), (UNIT_MOHM, "MΩ"))`.
2. `bjt_bias/app.py` — pass `resistor_units=RESISTOR_UNITS` and the existing
   default `kohm` into the template.
3. `bjt_bias/templates/index.html` — replace the two hardcoded `<option>` lines
   with a loop over `resistor_units`; keep `kΩ` as the default selection.
4. `README.md`, `bjt_bias/README.md` — document the third unit and show `1 MΩ`
   as an equivalent A2 entry.
5. `docs/validation.md` — add an MΩ check and a clearly labelled **Fixed bias
   independent verification** section (hand calculation + browser observation).

## Verification the builder must run

- RED→GREEN one-off assertion: `rb=1, rb_unit=mohm` yields `rb == 1e6` and
  `IC 1.13 mA / VCE 9.514 V`; `rb_unit=bogus` still errors.
- Independent Fixed check with several cases computed outside the app, e.g.
  `VCC=12, RB=470 kΩ, RC=2.2 kΩ, β=100, VBE=0.7` → hand result, then compare
  with the page. Include the A2 `1 MΩ` case.
- Real Chrome via the existing throwaway Playwright script: submit A2 with
  `RB = 1 MΩ` and confirm the DOM shows `9.514 V`; keep the A2 evidence updated.
- `pytest bjt_bias\tests -q` → 43 passed.
- `git diff --check` clean.

## What is left to the builder

Follow a short plan from `writing-plans`; report the Fixed-bias verdict with
actual numbers, not just "looks right".
