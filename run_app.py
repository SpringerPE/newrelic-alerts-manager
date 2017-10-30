from os import environ
import sys

from flask import Flask, render_template

from newrelic_alerting.api import api
from newrelic_alerting.config import AppConfig

def create_app(config):
    app = Flask(__name__)

    app.config.from_object(config)
    app.register_blueprint(api, url_prefix="/api")

    @app.route("/")
    def index():
        return render_template("index.html")

    return app


if __name__ == '__main__':

    config = AppConfig()
    try:
        config.load_app_config()
    except Exception as e:
        print(e)
        sys.exit(1)

    app = create_app(config)

    if "PORT" in environ:
        app.run("0.0.0.0", int(environ["PORT"]))
    else:
        app.debug = config.DEBUG
        app.run()
