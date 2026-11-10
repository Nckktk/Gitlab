from flask import Flask, render_template, request

from bjt_bias.engineering import analyze, parse_inputs


def create_app() -> Flask:
    app = Flask(__name__)

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
