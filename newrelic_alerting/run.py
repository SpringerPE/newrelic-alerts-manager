import requests
import sys
from os import environ

from flask import Flask, url_for, render_template

from newrelic_alerting.api import api
from newrelic_alerting.config import AppConfig

from .config import CLIConfig
from .server import ServersManager, ServersDataManager
from .policy import PolicyDataManager, PoliciesManager
from .alert_manager import NewRelicAlertManager
from . import helper

logger = helper.getLogger(__name__)

def run_synch(config):

    session = requests.Session()
    if config["API_KEY"] == "":
        raise Exception("New Relic API key cannot be empty")
    session.headers.update({'X-Api-Key': config["API_KEY"]})

    sdm = ServersDataManager(session)
    sm = ServersManager(sdm)
    sm.max_inactivity = config["MAX_INACTIVITY"]
    sm.cleanup_not_reporting_servers()

    pdm = PolicyDataManager(session)
    pm = PoliciesManager(pdm)
    alert_manager = NewRelicAlertManager(session, config["ALERT_CONFIG"]["alert_policies"], pm, sm)
    alert_manager.initialise()
    alert_manager.assign_servers_to_policies()

def main():

    config = CLIConfig()
    config.load_cli_config()
    logger.info(config)

    run_synch(dict(config))

def create_app(config):
    app = Flask(__name__)

    app.config.from_object(config)
    app.register_blueprint(api, url_prefix="/api")

    @app.route("/")
    def index():
        index_css_url =  url_for('static', filename='styles/index.css')
        return render_template("index.html.j2", index_css_url=index_css_url)

    return app


def main_app():

    config = AppConfig()
    try:
        config.load_app_config()
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    logger.info(config)
    app = create_app(config)

    if "PORT" in environ:
        app.run("0.0.0.0", int(environ["PORT"]))
    else:
        app.debug = config.DEBUG
        app.run()