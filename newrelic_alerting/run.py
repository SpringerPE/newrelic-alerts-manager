import yaml
import json
import requests
import logging
import os
import sys, getopt

from .server import ServersManager, ServersDataManager
from .policy import PolicyDataManager, PoliciesManager
from .alert_manager import NewRelicAlertManager
from . import helper

logger = helper.getLogger(__name__)

def run_synch(key="", config={}, debug=False):

    session = requests.Session()
    if key == "":
        raise Exception("New Relic API key cannot be empty")
    session.headers.update({'X-Api-Key': key})

    sdm = ServersDataManager(session)
    sm = ServersManager(sdm)
    sm.cleanup_not_reporting_servers()

    pdm = PolicyDataManager(session)
    pm = PoliciesManager(pdm)
    alert_manager = NewRelicAlertManager(session, config["alert_policies"], pm, sm)
    alert_manager.initialise()
    alert_manager.assign_servers_to_policies()

def main_app():

    if 'VCAP_SERVICES' in os.environ:
        services = json.loads(os.getenv('VCAP_SERVICES'))
        key = services["newrelic"][0]["credentials"]["licenseKey"]
        print("The key is" + key)

    elif "NEWRELIC_KEY" in os.environ:
        key = os.getenv("NEWRELIC_KEY")

    else:
        logging.error("The variable NEWRELIC_KEY needs to be defined")
        raise Exception("The variable NEWRELIC_KEY needs to be defined")

    if 'ALERT_CONFIG' in os.environ:
        alert_config = yaml.load(os.getenv("ALERT_CONFIG"))
    else:
        logging.error("The variable ALERT_CONFIG needs to be defined")
        raise Exception("The variable ALERT_CONFIG needs to be defined")

    debug = os.environ.get("ALERT_MANAGER_DEBUG_LOG", False)

    run_synch(key, alert_config, debug)

def main():

    argv = sys.argv[1:]

    key = ""
    debug = False

    usage_string = "newrelic_alerting -k <newrelic_key> [-d]"
    try:
            opts, args = getopt.getopt(argv,"hk:", ["key="])
    except getopt.GetoptError:
            logger.error(usage_string)
            sys.exit(2)
    for opt, arg in opts:
            if opt == '-h':
                logger.info(usage_string)
                sys.exit()
            elif opt in ("-k", "--key"):
                    key = arg
            elif opt in ("-d"):
                    debug = True

            if debug:
                logger.setLevel(logging.DEBUG)

    with open("./alert_config.yml") as alert_config_file:
        config = yaml.load(alert_config_file)

    run_synch(key, config, debug)

