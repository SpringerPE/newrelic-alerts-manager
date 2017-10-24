import logging
import pytz

from dateutil.parser import parse
from datetime import timedelta, datetime

from . import pagination 


logging.basicConfig()
logger = logging.getLogger('ServersManager')
logger.setLevel(logging.INFO)

class ServersDataManager(object):

    servers_url = "https://api.newrelic.com/v2/servers.json"
    server_delete_url = "https://api.newrelic.com/v2/servers/{server_id}.json"

    def __init__(self, session):
        self.session = session

    def delete_server(self, server_id, params):
            response = self.session.delete(self.server_delete_url.format(
                server_id=server["id"], params=params))

            if response.status_code == 200:
                logger.info("Server successfully deleted")
                return True
            else:
                logger.error(response.json())
                logger.info("Error while deleting the server")
                return False

    def get_servers(self, params=None):
        return pagination.entities(self.servers_url, self.session, "servers", params=params)

class ServersManager(object):

    def __init__(self, sdm):
        self.sdm = sdm

    def get_servers(self, params=None):
        return self.sdm.get_servers(params)


    def get_not_reporting_servers(self, hours):

        params ={"filter[reported]": "false"}
        all_servers = self.get_servers(params)

        delete_since = timedelta(hours=hours)

        now = datetime.utcnow().replace(tzinfo=pytz.utc)
        not_reporting_servers = [
            server for server in all_servers 
            if not server["reporting"] 
            if now - parse(server["last_reported_at"]) > delete_since
        ]
        return not_reporting_servers

    def cleanup_not_reporting_servers(self, hours=24):

        not_reporting_servers = self.get_not_reporting_servers(hours)

        print(not_reporting_servers)
        for server in not_reporting_servers:
            logger.info("Permanently deleting server: {}".format(server["name"]))
            response = self.sdm.delete_server(server["id"], params)
