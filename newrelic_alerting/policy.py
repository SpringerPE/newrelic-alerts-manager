from . import pagination
from . import helper

logger = helper.getLogger(__name__)

class PolicyDataManager(object):

    alert_policies_url = "https://api.newrelic.com/v2/alerts_policies.json"
    alert_conditions_url = "https://api.newrelic.com/v2/alerts_conditions.json"
    alerts_entity_conditions_url = "https://api.newrelic.com/v2/alerts_entity_conditions/{entity_id}.json"

    def __init__(self, session):
        self.session = session

    def all_policies(self, params=None):

        policies = pagination.entities(self.alert_policies_url, self.session, "policies", params=params)
        return policies

    def all_conditions(self, params=None):

        conditions = pagination.entities(self.alert_conditions_url, self.session, "conditions", params=params)
        return conditions

    @pagination.handle_response
    def deregister_server(self, server_id, condition_id):

        delete_server_from_policy_url = self.alerts_entity_conditions_url.format(entity_id=server_id)
        params = {
            "entity_type": "Server",
            "condition_id": condition_id
        }
        logger.info("REMOVING entity: {} from condition: {}".format(server_id, condition_id))

        response = self.session.delete(delete_server_from_policy_url, params=params)
        return response

    @pagination.handle_response
    def register_server(self, server, condition_id):
        server_id = server["id"]
        add_server_to_policy_url = self.alerts_entity_conditions_url.format(entity_id=server_id)

        params = {
            "entity_type": "Server",
            "condition_id": condition_id
        }

        logger.info("ADDING entity: {} to condition: {}".format(server["name"], condition_id))

        response = self.session.put(add_server_to_policy_url, params=params)
        return response


class PoliciesManager(object):
    def __init__(self, pdm):
        self.pdm = pdm
        self.alert_policies = []

    def add_alert_policy(self, policy):
        new_policy = Policy(self.pdm, policy)
        new_policy.initialise()
        self.alert_policies.append(new_policy)

    def policies_by_tags(self, tags):
        tags = set(tags)

        return [policy for policy in self.alert_policies if not tags.isdisjoint(policy.tags)]

    def __str__(self):
        toText = ""
        for policy in self.alert_policies:
            toText += str(policy)
        return toText


class Policy(object):
    def __init__(self, pdm, policy):
        self.pdm = pdm
        self.tags = set(policy["tags"])
        self.name = policy["name"]
        self.id = ""
        self.cm = ConditionManager(pdm)

    def initialise(self):
        params = {"filter[name]": self.name}
        policies = self.pdm.all_policies(params)
        this_policy = policies[0]
        self.id = this_policy["id"]
        self.cm.add_conditions(self.id)

    def register_server(self, server):
        self.cm.register_server(server)

    def deregister_servers(self, servers_to_keep):
        self.cm.deregister_servers(servers_to_keep)

    def __str__(self):
        return ("{ Name: " + self.name + " },"
                "{ id: " + str(self.id) + " },"
                "{ tags: " + str(self.tags) + " }"
                "{ conditions: " + str(self.cm) + "}")


class ConditionManager(object):
    def __init__(self, pdm):
        self.pdm = pdm
        self.conditions = []

    def add_conditions(self, policy_id):
        params = {"policy_id": policy_id}
        conditions = self.pdm.all_conditions(params=params)
        for condition in conditions:
            self.conditions.append(Condition(self.pdm, condition))

    def deregister_servers(self, servers_to_keep):
        for condition in self.conditions:
            condition.deregister_servers(servers_to_keep)

    def register_server(self, server):
        for condition in self.conditions:
            condition.register_server(server)

    def __str__(self):
        toText = ""
        for condition in self.conditions:
            toText += str(condition)
        return toText


class Condition(object):
    def __init__(self, pdm, condition):
        self.pdm = pdm
        self.entities = set(condition["entities"])
        self.name = condition["name"]
        self.id = condition["id"]

    def __str__(self):
        return (
            "{ Name: " + self.name + " },"
            "{ id: " + str(self.id) + " },"
            "{ entities: " + str(self.entities) + " }")

    def __iter__(self):
        return iter(self.entities)

    def deregister_servers(self, servers_to_keep):
        server_to_keep_ids = set([str(server["id"]) for server in servers_to_keep])

        redundant_ids = self.entities - server_to_keep_ids

        for server_id in redundant_ids:
            self.deregister_server(server_id)

    def deregister_server(self, server_id):
        if str(server_id) in self.entities:
            ok = self.pdm.deregister_server(server_id, self.id)
            if ok:
                self.entities.discard(str(server_id))

    def register_server(self, server):
        server_id = server["id"]
        if str(server_id) not in self.entities:
            ok = self.pdm.register_server(server, self.id)
            if ok:
                self.entities.add(str(server_id))
