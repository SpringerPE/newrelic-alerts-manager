import yaml
import json
import requests
import sys, getopt
import logging
import pytz
from dateutil.parser import parse
from datetime import timedelta, datetime

logging.basicConfig()
logger = logging.getLogger('AlertManager')
logger.setLevel(logging.INFO)

def pages(url, session, params=None):
    response = session.get(url, params=params)
    yield response
    while True:
        try:
            next_url = response.links['next']['url']
            response = session.get(next_url)
            yield response
        except KeyError:
            break

def entities(url, session, entity_name, params=None):
    entities = []

    for response in pages(url, session, params=params):
        json_response = response.json()
        if entity_name in json_response:
            entities[0:0] = json_response[entity_name]

    return entities

class NewRelicAlertManager(object):

    def __init__(self, session, config, policy_manager, server_manager):
        self.session = session
        self.config = config
        self.pm = policy_manager
        self.sm = server_manager
        self.initialise()

    def initialise(self):
        for alert_policy in self.config:
            self.pm.add_alert_policy(alert_policy)

    def assign_servers_to_policies(self):
        logger.info("Refreshing server policies...")
        for policy in self.pm.alert_policies:
            tags = []
            for tag in policy.tags:
                tags.append("Deployment:" + tag)
            params= {"filter[labels]": ";".join(tags)}
            servers = self.sm.get_servers(params=params)
            for server in servers:
                policy.register_server(server)
            #cleanup the policy
            policy.deregister_servers(servers)

class ConditionManager(object):
    alert_conditions_url = "https://api.newrelic.com/v2/alerts_conditions.json"

    def __init__(self, session):
        self.session = session
        self.conditions = []

    def add_conditions(self, policy_id):
        params = {"policy_id": policy_id}
        conditions = entities(self.alert_conditions_url, self.session, "conditions", params=params)
        for condition in conditions:
            self.conditions.append(Condition(self.session, condition))

    def deregister_server(self, server):
        for condition in self.conditions:
            condition.deregister_server(server)

    def register_server(self, server):
        for condition in self.conditions:
            condition.register_entities(server)

    def __str__(self):
        toText = ""
        for condition in self.conditions:
            toText += str(condition)
        return toText

class Condition(object):
    alerts_entity_conditions_url = "https://api.newrelic.com/v2/alerts_entity_conditions/{entity_id}.json"

    def __init__(self, session, condition):
        self.session = session
        self.entities = set(condition["entities"])
        self.name = condition["name"]
        self.id = condition["id"]

    def __str__(self):
        return (
            "{ Name: " + self.name + " },"
            "{ id: " + str(self.id) +" },"
            "{ entities: " + str(self.entities) +" }")

    def deregister_servers(self, servers):
        server_ids = set([ str(server["id"]) for server in servers ])
        redundant_ids = self.entities - server_ids

        redundant_servers = [ server for server in servers if server["id"] in redundant_ids ]
        for server in redundant_servers:
            self.deregister_server(server)

    def deregister_server(self, server):
        server_id = server["id"]
        if str(server_id) in self.entities:
            delete_server_from_policy_url = self.alerts_entity_conditions_url.format(entity_id=server_id)

            params = {
                "entity_type": "Server",
                "condition_id": self.id
            }
            response = self.session.delete(delete_server_from_policy_url, params=params)
            logger.info("REMOVING entity: {} from condition: {}".format(server["name"], self.name))

            try:
                responses = response.json()
                self.entities = set([ str(entity) for entity in responses["condition"]["entities"] ])
            except ValueError:
                logger.error("Error while parsing the json response")

    def register_server(self, server):
        server_id = server["id"]
        if str(server_id) not in self.entities:
            add_server_to_policy_url = self.alerts_entity_conditions_url.format(entity_id=server_id)
            params = {
                "entity_type": "Server",
                "condition_id": self.id
            }
            response = self.session.put(add_server_to_policy_url, params=params)
            logger.info("ADDING entity: {} to condition: {}".format(server["name"], self.name))

            try:
                responses = response.json()
                self.entities = set([ str(entity) for entity in responses["condition"]["entities"] ])
            except ValueError:
                logger.error("Error while parsing the json response")

class PoliciesManager(object):

    def __init__(self, session):
        self.session = session
        self.alert_policies = []

    def add_alert_policy(self, policy):
            self.alert_policies.append(Policy(self.session, policy))

    def policies_by_tags(self, tags):
        return [ policy for policy in self.alert_policies if not tags.isdisjoint(policy.tags) ]

    def __str__(self):
        toText = ""
        for policy in self.alert_policies:
            toText += str(policy)
        return toText

class Policy(object):
    
    alert_policies_url = "https://api.newrelic.com/v2/alerts_policies.json"
    alert_conditions_url = "https://api.newrelic.com/v2/alerts_conditions.json"

    def __init__(self, session, policy):
        self.session = session
        self.tags = set(policy["tags"])
        self.name = policy["name"]
        self.id = ""
        self.cm = ConditionManager(session)
        servers = []
        self.initialise()

    def initialise(self):
        params = {"filter[name]": self.name}
        policies = entities(self.alert_policies_url, self.session, "policies", params=params)
        this_policy = policies[0]
        self.id = this_policy["id"]
        self.cm.add_conditions(self.id)

    def register_server(self, server):
        for condition in self.cm.conditions:
            condition.register_server(server)

    def deregister_servers(self, servers):
        for condition in self.cm.conditions:
            condition.deregister_servers(servers)

    def __str__(self):
        return ("{ Name: " + self.name + " },"
            "{ id: " + str(self.id) +" },"
            "{ tags: " + str(self.tags) +" }"
            "{ conditions: " + str(self.cm) + "}" )

class ServersManager(object):

    servers_url = "https://api.newrelic.com/v2/servers.json"
    server_delete_url = "https://api.newrelic.com/v2/servers/{server_id}.json"

    delete_policy = ""
    def __init__(self, session):
        self.session = session
        self.delete_delay = timedelta(hours=24)

    def get_servers(self, params=None):
        return entities(self.servers_url, self.session, "servers", params=params)

    def cleanup_not_reporting_servers(self):
        params ={"filter[reported]": "false"}
        all_servers = self.get_servers(params)
        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        not_reporting_servers = [ server for server in all_servers 
            if not server["reporting"] 
            if now - parse(server["last_reported_at"]) > self.delete_delay]
        
        for server in not_reporting_servers:
            logger.info("Permanently deleting server: {}".format(server["name"]))
            response = self.session.delete(self.server_delete_url.format(
                server_id=server["id"], params=params))

            if response.status_code == 200:
                logger.info("Server successfully deleted")
            else:
                logger.error(response.json())
                logger.info("Error while deleting the server")



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

    sm = ServersManager(session)
    sm.cleanup_not_reporting_servers()

    pm = PoliciesManager(session) 
    alert_manager = NewRelicAlertManager(session, config["alert_policies"], pm, sm)
    alert_manager.assign_servers_to_policies()

if __name__ == '__main__':
    main(sys.argv[1:])
