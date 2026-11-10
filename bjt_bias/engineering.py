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
