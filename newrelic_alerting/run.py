from .server import ServersManager, ServersDataManager
import yaml
import requests
import sys, getopt

def main(argv):

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

    session = requests.Session()
    if key == "":
        logger.critical("New Relic API key cannot be empty")
        sys.exit(1)
    session.headers.update({'X-Api-Key': key})

    sdm = ServersDataManager(session)
    sm = ServersManager(sdm)
    sm.cleanup_not_reporting_servers()

    # pm = PoliciesManager(session) 
    # alert_manager = NewRelicAlertManager(session, config["alert_policies"], pm, sm)
    # alert_manager.initialise()
    # alert_manager.assign_servers_to_policies()
