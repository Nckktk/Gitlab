"""Engineering logic for BJT common-emitter DC bias.

Pure functions only: this module must never import Flask.
"""

import math
from dataclasses import dataclass

VCE_SAT = 0.2
FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")

_NUMBER_ERROR = "ต้องเป็นตัวเลข"
_POSITIVE_ERROR = "ต้องมากกว่าศูนย์"


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
    """Turn raw form strings into validated inputs, or per-field Thai errors."""
    values: dict[str, float] = {}
    errors: dict[str, str] = {}

    for field in FIELDS:
        text = (raw.get(field) or "").strip()
        if not text:
            errors[field] = _NUMBER_ERROR
            continue
        try:
            value = float(text)
        except ValueError:
            errors[field] = _NUMBER_ERROR
            continue
        if not math.isfinite(value):
            errors[field] = _NUMBER_ERROR
            continue
        values[field] = value

    if "vcc" in values and values["vcc"] <= 0:
        errors["vcc"] = _POSITIVE_ERROR
    for field in ("r1", "r2", "rc", "re"):
        if field in values and values[field] <= 0:
            errors[field] = _POSITIVE_ERROR
    if "beta" in values and values["beta"] <= 0:
        errors["beta"] = _POSITIVE_ERROR
    if "vbe" in values:
        if values["vbe"] < 0:
            errors["vbe"] = "ต้องไม่ติดลบ"
        elif "vcc" in values and values["vbe"] >= values["vcc"]:
            errors["vbe"] = "ต้องน้อยกว่า VCC"

    if errors:
        return None, errors
    return BiasInputs(**values), {}


def solve_thevenin(i: BiasInputs) -> dict[str, float]:
    """Solve the bias point with a Thevenin equivalent of the base divider."""
    vbb = i.vcc * i.r2 / (i.r1 + i.r2)
    rb = i.r1 * i.r2 / (i.r1 + i.r2)
    ib = (vbb - i.vbe) / (rb + (i.beta + 1) * i.re)
    ic = i.beta * ib
    ie = (i.beta + 1) * ib
    ve = ie * i.re
    vc = i.vcc - ic * i.rc
    return {
        "vbb": vbb,
        "rb": rb,
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "vb": ve + i.vbe,
        "ve": ve,
        "vc": vc,
        "vce": vc - ve,
    }


REL_TOL = 1e-9


def solve_nodal(i: BiasInputs) -> dict[str, float]:
    """Solve the same bias point by nodal analysis (independent formulation).

    With VB = VE + VBE, KCL at the base and emitter nodes collapses to one
    linear equation in VE.
    """
    conductance = 1 / i.r1 + 1 / i.r2 + 1 / ((i.beta + 1) * i.re)
    drive = i.vcc / i.r1 - i.vbe / i.r1 - i.vbe / i.r2
    ve = drive / conductance
    ie = ve / i.re
    ic = i.beta / (i.beta + 1) * ie
    ib = ie / (i.beta + 1)
    vc = i.vcc - ic * i.rc
    return {
        "vbb": i.vcc * i.r2 / (i.r1 + i.r2),
        "rb": i.r1 * i.r2 / (i.r1 + i.r2),
        "ib": ib,
        "ic": ic,
        "ie": ie,
        "vb": ve + i.vbe,
        "ve": ve,
        "vc": vc,
        "vce": vc - ve,
    }


def _rel_diff(a: float, b: float) -> float:
    return abs(a - b) / max(abs(a), abs(b), 1e-12)


def cross_check(
    a: dict[str, float], b: dict[str, float]
) -> tuple[bool, float]:
    """Compare the two independent solvers on IC and VCE."""
    diff = max(_rel_diff(a["ic"], b["ic"]), _rel_diff(a["vce"], b["vce"]))
    return (diff <= REL_TOL, diff)
