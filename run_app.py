from os import environ

from flask import Flask, render_template

from newrelic_alerting.api import api

def create_app():
    app = Flask(__name__)
    app.register_blueprint(api, url_prefix="/api")


    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == '__main__':

    app = create_app()

    if "PORT" in environ:
        app.run("0.0.0.0", int(environ["PORT"]))
    else:
        app.debug = True
        app.run()