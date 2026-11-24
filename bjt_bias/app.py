from flask import Flask, render_template, request

from bjt_bias.engineering import (
    ALL_RESISTOR_FIELDS,
    MODE_DIVIDER,
    MODE_EMITTER,
    MODE_FIXED,
    MODE_LABELS,
    MODES,
    UNIT_OHM,
    analyze_mode,
)
from bjt_bias.spice_engine import (
    DEFAULT_AC_FSTOP_HZ,
    DEFAULT_AC_FSTART_HZ,
    DEFAULT_BJT_MODEL_NAME,
    DEFAULT_SOURCE_AMPLITUDE_MV,
    DEFAULT_SOURCE_FREQUENCY_HZ,
    MAX_SOURCE_AMPLITUDE_MV,
    MAX_SOURCE_FREQUENCY_HZ,
    MIN_SOURCE_FREQUENCY_HZ,
    SpiceError,
    SpiceRunConfig,
    ngspice_available,
    ngspice_version,
    run_analysis,
)


MODE_FIELDS_META = {
    MODE_DIVIDER: [
        ("vcc", "VCC", "V"),
        ("r1", "R1", "resistor"),
        ("r2", "R2", "resistor"),
        ("rc", "RC", "resistor"),
        ("re", "RE", "resistor"),
        ("beta", "β", "β"),
        ("vbe", "VBE", "V"),
    ],
    MODE_FIXED: [
        ("vcc", "VCC", "V"),
        ("rb", "RB", "resistor"),
        ("rc", "RC", "resistor"),
        ("beta", "β", "β"),
        ("vbe", "VBE", "V"),
    ],
    MODE_EMITTER: [
        ("vcc", "VCC", "V"),
        ("rb", "RB", "resistor"),
        ("rc", "RC", "resistor"),
        ("re", "RE", "resistor"),
        ("beta", "β", "β"),
        ("vbe", "VBE", "V"),
    ],
}

SPICE_ANALYSES = ("op", "ac", "tran")
SPICE_ANALYSIS_LABELS = {"op": "DC (.op)", "ac": "AC (.ac)", "tran": "Transient (.tran)"}


def fmt_current(amps: float) -> str:
    """Show a current in the unit that keeps it readable, 6 significant figures."""
    magnitude = abs(amps)
    if magnitude >= 1:
        return f"{amps:.6g} A"
    if magnitude >= 1e-3:
        return f"{amps * 1e3:.6g} mA"
    if magnitude >= 1e-6:
        return f"{amps * 1e6:.6g} µA"
    if magnitude >= 1e-9:
        return f"{amps * 1e9:.6g} nA"
    return f"{amps:.6g} A"


def fmt_voltage(volts: float) -> str:
    """Show a voltage in volts, 6 significant figures."""
    return f"{volts:.6g} V"


def normalize_units(form: dict[str, str]) -> dict[str, str]:
    """Make the unit actually used visible on the rendered form.

    A submission without resistor unit keys is solved in ohms, so the form must
    not fall back to its kΩ default and claim a unit the numbers did not use.
    """
    normalized = dict(form)
    for field in ALL_RESISTOR_FIELDS:
        if not (normalized.get(f"{field}_unit") or "").strip():
            normalized[f"{field}_unit"] = UNIT_OHM
    return normalized


def _parse_float(raw: str, field: str, errors: dict[str, str], *, positive: bool = True) -> float | None:
    text = (raw or "").strip()
    if not text:
        errors[field] = "ต้องเป็นตัวเลข"
        return None
    try:
        value = float(text)
    except ValueError:
        errors[field] = "ต้องเป็นตัวเลข"
        return None
    if not (value == value and abs(value) != float("inf")):
        errors[field] = "ต้องเป็นตัวเลข"
        return None
    if positive and value <= 0:
        errors[field] = "ต้องมากกว่าศูนย์"
        return None
    if value < 0:
        errors[field] = "ต้องไม่ติดลบ"
        return None
    return value


def _build_spice_config(form: dict[str, str]) -> tuple[SpiceRunConfig | None, dict[str, str], dict[str, str]]:
    errors: dict[str, str] = {}
    # Use divider fields as the CE reference circuit parameters.
    vcc = _parse_float(form.get("vcc", ""), "vcc", errors)
    beta = _parse_float(form.get("beta", ""), "beta", errors)
    vbe = _parse_float(form.get("vbe", ""), "vbe", errors, positive=False)
    if vbe is not None and vbe < 0:
        errors["vbe"] = "ต้องไม่ติดลบ"

    def parse_res(name: str) -> float | None:
        value = _parse_float(form.get(name, ""), name, errors)
        if value is None:
            return None
        unit = (form.get(f"{name}_unit") or UNIT_OHM).strip()
        factor = 1.0 if unit == UNIT_OHM else 1000.0 if unit == "kohm" else None
        if factor is None:
            errors[name] = "หน่วยไม่ถูกต้อง"
            return None
        scaled = value * factor
        if scaled <= 0:
            errors[name] = "ต้องมากกว่าศูนย์"
            return None
        return scaled

    r1 = parse_res("r1")
    r2 = parse_res("r2")
    rc = parse_res("rc")
    re = parse_res("re")
    rl = parse_res("rl")
    cin_u = _parse_float(form.get("cin_u", "10"), "cin_u", errors)
    cout_u = _parse_float(form.get("cout_u", "10"), "cout_u", errors)
    amp = _parse_float(form.get("amplitude_mv", str(DEFAULT_SOURCE_AMPLITUDE_MV)), "amplitude_mv", errors)
    freq = _parse_float(form.get("frequency_hz", str(DEFAULT_SOURCE_FREQUENCY_HZ)), "frequency_hz", errors)

    if amp is not None and amp > MAX_SOURCE_AMPLITUDE_MV:
        errors["amplitude_mv"] = f"ต้องไม่เกิน {MAX_SOURCE_AMPLITUDE_MV:g} mV"
    if freq is not None and (freq < MIN_SOURCE_FREQUENCY_HZ or freq > MAX_SOURCE_FREQUENCY_HZ):
        errors["frequency_hz"] = f"ต้องอยู่ระหว่าง {MIN_SOURCE_FREQUENCY_HZ:g} Hz ถึง {MAX_SOURCE_FREQUENCY_HZ:g} Hz"
    if vcc is not None and vbe is not None and vbe >= vcc:
        errors["vbe"] = "ต้องน้อยกว่า VCC"

    values = {"amplitude_mv": amp, "frequency_hz": freq}
    if errors or None in (vcc, r1, r2, rc, re, rl, cin_u, cout_u, beta, vbe, amp, freq):
        return None, errors, {k: str(v) for k, v in form.items()}

    config = SpiceRunConfig(
        vcc=vcc,
        r1=r1,
        r2=r2,
        rc=rc,
        re=re,
        rl=rl,
        cin=cin_u * 1e-6,
        cout=cout_u * 1e-6,
        beta=beta,
        vbe=vbe,
        amplitude_mv=amp,
        frequency_hz=freq,
    )
    return config, {}, {}


def create_app() -> Flask:
    app = Flask(__name__)
    app.add_template_filter(fmt_current, "current")
    app.add_template_filter(fmt_voltage, "voltage")

    @app.route("/", methods=["GET", "POST"])
    def index():
        spice_result = None
        spice_error = None
        spice_analysis = "op"

        if request.method == "POST":
            form = normalize_units(request.form.to_dict())
            mode = (form.get("mode") or MODE_DIVIDER).strip()
            fields = MODE_FIELDS_META.get(mode, MODE_FIELDS_META[MODE_DIVIDER])
            spice_analysis = (form.get("spice_analysis") or "op").strip()
            if spice_analysis not in SPICE_ANALYSES:
                spice_analysis = "op"

            if "change_mode" in request.form:
                return render_template(
                    "index.html",
                    form=form,
                    errors={},
                    result=None,
                    mode=mode,
                    mode_label=MODE_LABELS.get(mode, mode),
                    modes=MODES,
                    mode_labels=MODE_LABELS,
                    fields=fields,
                    spice_result=None,
                    spice_error=None,
                    spice_analysis=spice_analysis,
                    spice_analyses=SPICE_ANALYSES,
                    spice_analysis_labels=SPICE_ANALYSIS_LABELS,
                    spice_available=ngspice_available(),
                    spice_version=ngspice_version() or "ไม่พบ",
                    default_bjt_model=DEFAULT_BJT_MODEL_NAME,
                )

            if "run_spice" in request.form:
                # Preserve analytical result display for divider inputs when possible.
                result = None
                errors: dict[str, str] = {}
                if mode in MODES:
                    result, errors = analyze_mode(mode, form)
                    # For SPICE run, we still show analytical result if valid; spice errors are separate.
                config, spice_errors, _ = _build_spice_config(form)
                errors.update(spice_errors)
                if config is None:
                    spice_error = "ข้อมูลสำหรับ SPICE ไม่ถูกต้อง: " + "; ".join(
                        f"{k}: {v}" for k, v in spice_errors.items()
                    )
                else:
                    try:
                        spice_result = run_analysis(config, spice_analysis)
                    except SpiceError as exc:
                        spice_error = str(exc)
                    except Exception as exc:
                        spice_error = f"เกิดข้อผิดพลาดที่ไม่คาดคิด: {exc}"
                # Do not block page render on analytical errors; SPICE section shows its own status.
                if errors and result is None and mode != MODE_DIVIDER:
                    # keep analytical errors visible
                    pass
                return render_template(
                    "index.html",
                    form=form,
                    errors=errors,
                    result=result,
                    mode=mode,
                    mode_label=MODE_LABELS.get(mode, mode),
                    modes=MODES,
                    mode_labels=MODE_LABELS,
                    fields=fields,
                    spice_result=spice_result,
                    spice_error=spice_error,
                    spice_analysis=spice_analysis,
                    spice_analyses=SPICE_ANALYSES,
                    spice_analysis_labels=SPICE_ANALYSIS_LABELS,
                    spice_available=ngspice_available(),
                    spice_version=ngspice_version() or "ไม่พบ",
                    default_bjt_model=DEFAULT_BJT_MODEL_NAME,
                )

            result, errors = analyze_mode(mode, form)
            return render_template(
                "index.html",
                form=form,
                errors=errors,
                result=result,
                mode=mode,
                mode_label=MODE_LABELS.get(mode, mode),
                modes=MODES,
                mode_labels=MODE_LABELS,
                fields=fields,
                spice_result=None,
                spice_error=None,
                spice_analysis=spice_analysis,
                spice_analyses=SPICE_ANALYSES,
                spice_analysis_labels=SPICE_ANALYSIS_LABELS,
                spice_available=ngspice_available(),
                spice_version=ngspice_version() or "ไม่พบ",
                default_bjt_model=DEFAULT_BJT_MODEL_NAME,
            )

        form = {}
        mode = MODE_DIVIDER
        return render_template(
            "index.html",
            form=form,
            errors={},
            result=None,
            mode=mode,
            mode_label=MODE_LABELS[mode],
            modes=MODES,
            mode_labels=MODE_LABELS,
            fields=MODE_FIELDS_META[mode],
            spice_result=None,
            spice_error=None,
            spice_analysis="op",
            spice_analyses=SPICE_ANALYSES,
            spice_analysis_labels=SPICE_ANALYSIS_LABELS,
            spice_available=ngspice_available(),
            spice_version=ngspice_version() or "ไม่พบ",
            default_bjt_model=DEFAULT_BJT_MODEL_NAME,
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
