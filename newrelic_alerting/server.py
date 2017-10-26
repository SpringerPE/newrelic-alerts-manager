import pytz
import requests

from dateutil.parser import parse
from datetime import timedelta, datetime

from . import pagination
from . import helper

logger = helper.getLogger(__name__)

class ServersDataManager(object):
    servers_url = "https://api.newrelic.com/v2/servers.json"
    server_delete_url = "https://api.newrelic.com/v2/servers/{server_id}.json"

    def __init__(self, session):
        self.session = session

    @pagination.handle_response
    def delete_server(self, server_id, params=None):
        response = self.session.delete(self.server_delete_url.format(
            server_id=server_id, params=params))
        return response

    def get_servers(self, params=None):
        return pagination.entities(self.servers_url, self.session, "servers", params=params)

class ServersManager(object):
    def __init__(self, sdm):
        self.sdm = sdm

    def get_servers(self, params=None):
        return self.sdm.get_servers(params)

    def get_not_reporting_servers(self, hours):
        """
        get a list of not reporting servers
        :param hours: the amount of hours since the server has been reporting
        :return: a list servers not reporting for longer than `hours` hours
        """
        params = {"filter[reported]": "false"}
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

        for server in not_reporting_servers:
            logger.info("Permanently deleting server: {}".format(server["name"]))
            ok = self.sdm.delete_server(server["id"])
            if not ok:
                logger.info("Failed deleting server: {}".format(server["name"]))
                return ok
        return True
