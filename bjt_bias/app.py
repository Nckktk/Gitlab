from flask import Flask, render_template, request

from bjt_bias.engineering import analyze, parse_inputs


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


def create_app() -> Flask:
    app = Flask(__name__)
    app.add_template_filter(fmt_current, "current")
    app.add_template_filter(fmt_voltage, "voltage")

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "POST":
            form = request.form.to_dict()
            inputs, errors = parse_inputs(form)
            result = analyze(inputs) if inputs is not None else None
            return render_template(
                "index.html", form=form, errors=errors, result=result
            )
        return render_template("index.html", form={}, errors={}, result=None)

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=True)
