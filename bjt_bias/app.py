from flask import Flask, render_template, request

from bjt_bias.engineering import (
    ALL_RESISTOR_FIELDS,
    MODE_DIVIDER,
    MODE_EMITTER,
    MODE_FIXED,
    MODES,
    UNIT_OHM,
    analyze_mode,
)

MODE_LABELS = {
    MODE_DIVIDER: "Voltage Divider Bias",
    MODE_FIXED: "Fixed Bias",
    MODE_EMITTER: "Emitter Bias",
}

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


def create_app() -> Flask:
    app = Flask(__name__)
    app.add_template_filter(fmt_current, "current")
    app.add_template_filter(fmt_voltage, "voltage")

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            form = normalize_units(request.form.to_dict())
            mode = (form.get("mode") or MODE_DIVIDER).strip()
            if form.get("change_mode"):
                result, errors = None, {}
            else:
                result, errors = analyze_mode(mode, form)
        else:
            form = {}
            mode = MODE_DIVIDER
            result, errors = None, {}

        return render_template(
            "index.html",
            form=form,
            errors=errors,
            result=result,
            mode=mode,
            mode_label=MODE_LABELS.get(mode, mode),
            modes=MODES,
            mode_labels=MODE_LABELS,
            fields=MODE_FIELDS_META.get(mode, MODE_FIELDS_META[MODE_DIVIDER]),
        )

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
