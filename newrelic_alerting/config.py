import os
import json
import sys
import getopt
import yaml

from contextlib import contextmanager

from .exceptions import NewRelicAlertingMissingConfVariable
from . import helper

logger = helper.getLogger(__name__)


class BaseConfig(object):
    MAX_INACTIVITY = 24
    DEBUG = False
    API_KEY = None
    ALERT_CONFIG = None

    def validate(self):
        mandatory = {
            "api_key": self.API_KEY,
            "alert config": self.ALERT_CONFIG
        }

        for description, value in mandatory.items():
            if value is None:
                raise NewRelicAlertingMissingConfVariable("The variable {} needs to be specified".format(description))

    def __iter__(self):
        yield 'MAX_INACTIVITY', self.MAX_INACTIVITY
        yield 'DEBUG', self.DEBUG
        yield 'API_KEY', self.API_KEY
        yield 'ALERT_CONFIG', self.ALERT_CONFIG

    def __str__(self):
        conf_string = """
        Configuration:
        
        MAX_INACTIVITY: {max_inactivity}
        DEBUG: {debug}
        ALERT_CONFIG: {alert_config}
        API_KEY: <redacted>
        """.format(max_inactivity=self.MAX_INACTIVITY, debug=self.DEBUG, alert_config=self.ALERT_CONFIG)

        return conf_string

class AppConfig(BaseConfig):

    def load_app_config(self):
        if 'VCAP_SERVICES' in os.environ:
            services = json.loads(os.getenv('VCAP_SERVICES'))
            self.API_KEY = services["newrelic"][0]["credentials"]["licenseKey"]
        else:
            self.API_KEY = os.getenv("NEWRELIC_API_KEY")

        self.ALERT_CONFIG = yaml.load(os.getenv("ALERT_CONFIG"))
        self.MAX_INACTIVITY = os.environ.get('SERVER_MAX_INACTIVITY', 24)
        self.DEBUG = os.environ.get("ALERT_MANAGER_DEBUG_LOG", False)

        self.validate()


class CLIConfig(BaseConfig):

    ALERT_CONF_FILE="./alert_config.yml"

    def load_cli_config(self):
        argv = sys.argv[1:]

        usage_string = "newrelic_alerting -k <newrelic_key> [-c <conf_file_path>] [-i <max_server_inactivity_in_hours] [-d]"
        try:
            opts, args = getopt.getopt(argv, "hk:c:i:", ["key="])
        except getopt.GetoptError:
            logger.error(usage_string)
            sys.exit(2)
        for opt, arg in opts:
            if opt == '-h':
                logger.info(usage_string)
                sys.exit()
            elif opt in ("-k", "--key"):
                self.API_KEY = arg
            elif opt in ("-i", "--max-server-inactivity"):
                self.MAX_INACTIVITY = int(arg)
            elif opt in ("-c", "--configuration-path"):
                self.ALERT_CONF_FILE = arg
            elif opt in ("-d", "--debug"):
                self.DEBUG = True

        with opened_w_error(self.ALERT_CONF_FILE) as (alert_config_file, err):
            if err:
                logger.error("The alerts configuration file was not found under the {} path".format(self.ALERT_CONF_FILE))
            else:
                self.ALERT_CONFIG = yaml.load(alert_config_file)

        self.validate()



@contextmanager
def opened_w_error(filename, mode="r"):
    try:
        f = open(filename, mode)
    except IOError as err:
        yield None, err
    else:
        try:
            yield f, None
        finally:
            f.close()