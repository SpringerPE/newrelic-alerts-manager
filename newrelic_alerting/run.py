import requests

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
    run_synch(dict(config))
