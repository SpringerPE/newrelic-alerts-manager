import yaml
import json
import requests
import sys, getopt
import logging
import pagination 

logging.basicConfig()
logger = logging.getLogger('AlertManager')
logger.setLevel(logging.INFO)

class NewRelicAlertManager(object):

    def __init__(self, session, config, policy_manager, server_manager):
        self.session = session
        self.config = config
        self.pm = policy_manager
        self.sm = server_manager

    def initialise(self):
        for alert_policy in self.config:
            self.pm.add_alert_policy(alert_policy)

    def assign_servers_to_policies(self):
        logger.info("Refreshing server policies...")
        for policy in self.pm.alert_policies:
            tags = []
            for tag in policy.tags:
                tags.append("Deployment:" + tag)
            params = {"filter[labels]": ";".join(tags)}
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
            new_policy = Policy(self.session, policy)
            new_policy.initialise()
            self.alert_policies.append(new_policy)

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
