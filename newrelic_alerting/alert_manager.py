from . import helper

logger = helper.getLogger(__name__)

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
        """
        Assign servers to policies based on their Deployment tag.
        ie. all the servers tagged as `dev` will be added to the
        policies whose tag list contains `dev`

        In addition to this all the unmatched servers will be deleted
        from the policy
        :return:
        """
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
        logger.info("DONE: Refreshing server policies...")


