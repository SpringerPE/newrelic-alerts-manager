import unittest
import requests
import requests_mock
import yaml
import json
import datetime
from newrelic_alerting.server import ServersManager, ServersDataManager

two_hours_ago = (
	datetime.datetime.utcnow() - datetime.timedelta(hours=2)
	).strftime('%Y-%m-%dT%H:%M:%S+00:00')

just_now = (datetime.datetime.utcnow()).strftime('%Y-%m-%dT%H:%M:%S+00:00')

all_servers = [
{
	'id': 86867839,
	'account_id': 1111111,
	'name': 'cell_z2-32-live-diego',
	'host': 'cell_z2-32-live-diego',
	'health_status': 'green',
	'reporting': True,
	'last_reported_at': just_now,
	'summary': {
		'cpu': 11.4,
		'cpu_stolen': 0.0,
		'disk_io': 0.03,
		'memory': 24.3,
		'memory_used': 6151995392,
		'memory_total': 25282215936,
		'fullest_disk': 38.6,
		'fullest_disk_free': 1861000000
	},
	'links': {}
},
{
	'id': 86713155,
	'account_id': 1111111,
	'name': 'cell_z2-33-dev-diego',
	'host': 'cell_z2-33-dev-diego',
	'health_status': 'green',
	'reporting': False,
	'last_reported_at': two_hours_ago,
	'summary': {
		'cpu': 11.4,
		'cpu_stolen': 0.0,
		'disk_io': 0.03,
		'memory': 24.3,
		'memory_used': 6151995392,
		'memory_total': 25282215936,
		'fullest_disk': 38.6,
		'fullest_disk_free': 1861000000
	},
	'links': {}
}]

class MockServersDataManager(object):

	def delete_server(self, server_id, params):
		pass

	def get_servers(self, params):
		return all_servers	

class TestServerManager(unittest.TestCase):
	
	def setUp(self):
		self.sdm = MockServersDataManager()

	def test_cleanup_not_reporting_servers(self):

		sm = ServersManager(self.sdm)

		not_reporting = sm.get_not_reporting_servers(1)

		self.assertEqual(len(not_reporting), 1)
		self.assertEqual(not_reporting[0]["id"], 86713155)
