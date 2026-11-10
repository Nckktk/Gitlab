"""Engineering logic for BJT common-emitter DC bias.

Pure functions only: this module must never import Flask.
"""

import math
from dataclasses import dataclass

VCE_SAT = 0.2
MAX_INPUT = 1e12
FIELDS = ("vcc", "r1", "r2", "rc", "re", "beta", "vbe")
RESISTOR_FIELDS = ("r1", "r2", "rc", "re")
UNIT_OHM = "ohm"
UNIT_KOHM = "kohm"
UNIT_FACTORS = {UNIT_OHM: 1.0, UNIT_KOHM: 1e3}

_NUMBER_ERROR = "ต้องเป็นตัวเลข"
_POSITIVE_ERROR = "ต้องมากกว่าศูนย์"
_TOO_LARGE_ERROR = "ค่ามากเกินไป"
_UNIT_ERROR = "หน่วยไม่ถูกต้อง"


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
        factor = 1.0
        if field in RESISTOR_FIELDS:
            unit = (raw.get(f"{field}_unit") or UNIT_OHM).strip()
            if unit not in UNIT_FACTORS:
                errors[field] = _UNIT_ERROR
                continue
            factor = UNIT_FACTORS[unit]
        try:
            value = float(text) * factor
        except ValueError:
            errors[field] = _NUMBER_ERROR
            continue
        if not math.isfinite(value):
            errors[field] = _NUMBER_ERROR
            continue
        if abs(value) > MAX_INPUT:
            errors[field] = _TOO_LARGE_ERROR
            continue
        values[field] = value

    if "vcc" in values and values["vcc"] <= 0:
        errors["vcc"] = _POSITIVE_ERROR
    for field in RESISTOR_FIELDS:
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


@dataclass(frozen=True)
class BiasResult:
    inputs: BiasInputs
    vbb: float
    rb: float
    ib: float
    ic: float
    ie: float
    vb: float
    ve: float
    vc: float
    vce: float
    region: str
    warning: str | None
    check_passed: bool
    check_max_rel_diff: float


def analyze(i: BiasInputs) -> BiasResult:
    """Cross-check the raw solutions, then classify the region.

    The cross-check always compares the raw solver outputs, before the
    cutoff boundary condition rewrites what is reported.
    """
    thevenin = solve_thevenin(i)
    nodal = solve_nodal(i)
    passed, diff = cross_check(thevenin, nodal)

    common = dict(
        inputs=i,
        vbb=thevenin["vbb"],
        rb=thevenin["rb"],
        check_passed=passed,
        check_max_rel_diff=diff,
    )

    if thevenin["ib"] <= 0:
        return BiasResult(
            **common,
            ib=0.0,
            ic=0.0,
            ie=0.0,
            vb=thevenin["vbb"],
            ve=0.0,
            vc=i.vcc,
            vce=i.vcc,
            region="cutoff",
            warning="Cutoff — ไม่มีกระแสไหลในวงจร (IB ≤ 0)",
        )

    if thevenin["vce"] <= VCE_SAT:
        region = "saturation"
        warning = "Saturation — ทรานซิสเตอร์ไม่ทำงานใน active region (VCE ≤ 0.2 V)"
    else:
        region = "active"
        warning = None

    return BiasResult(
        **common,
        ib=thevenin["ib"],
        ic=thevenin["ic"],
        ie=thevenin["ie"],
        vb=thevenin["vb"],
        ve=thevenin["ve"],
        vc=thevenin["vc"],
        vce=thevenin["vce"],
        region=region,
        warning=warning,
    )
