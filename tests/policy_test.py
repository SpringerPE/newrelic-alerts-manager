import unittest
import requests
import requests_mock
import yaml
import json
import datetime
from newrelic_alerting.policy import PoliciesManager, Policy

two_hours_ago = (
	datetime.datetime.utcnow() - datetime.timedelta(hours=2)
	).strftime('%Y-%m-%dT%H:%M:%S+00:00')

just_now = (datetime.datetime.utcnow()).strftime('%Y-%m-%dT%H:%M:%S+00:00')

config = yaml.load("""
---
alert_policies:
    - name: "Test Policy1"
      tags:
      - test1
      - test
    - name: "Test Policy2"
      tags:
      - test2
      - test
"""
)

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

all_policies = [
{
	"id": 111111,
	"incident_preference": "PER_POLICY",
	"name": "Test Policy1",
	"created_at": 1508508849476,
	"updated_at": 1508508875523
},
{
	"id": 222222,
	"incident_preference": "PER_POLICY",
	"name": "Test Policy2",
	"created_at": 1508508849476,
	"updated_at": 1508508875523
}]

all_conditions = [{
	"id": 111111,
	"type": "servers_metric",
	"name": "CPU % (High)",
	"enabled": True,
	"entities": [],
	"metric": "cpu_percentage",
      	"terms": [
	{
		"duration": "10",
		"operator": "above",
		"priority": "critical",
		"threshold": "90",
		"time_function": "all"
	},
	{
		"duration": "5",
		"operator": "above",
		"priority": "warning",
		"threshold": "85",
		"time_function": "all"
	}]
},
{
	"id": 222222,
	"type": "servers_metric",
	"name": "MEM % (High)",
	"enabled": True,
	"entities": [],
	"metric": "cpu_percentage",
      	"terms": [
	{
		"duration": "10",
		"operator": "above",
		"priority": "critical",
		"threshold": "90",
		"time_function": "all"
	},
	{
		"duration": "5",
		"operator": "above",
		"priority": "warning",
		"threshold": "85",
		"time_function": "all"
	}]
}
]

class MockPolicyDataManager(object):

	def delete_server(self, server_id, params):
		pass

	def all_policies(self, params):
		return all_policies	

	def all_conditions(self, params):
		return all_conditions

	def deregister_server(self, server_id, params):
		for condition in all_conditions:
			if server_id in condition["entities"]:
				condition["entities"].remove(server_id)
		return True

	def register_server(self, server, params):
		for condition in all_conditions:
			condition["entities"].append(server["id"])
		return True

class TestPolicyManager(unittest.TestCase):
	
	def setUp(self):
		self.pdm = MockPolicyDataManager()

	def test_add_alert_policy(self):

		pm = PoliciesManager(self.pdm)

		for alert_policy in config["alert_policies"]:
			pm.add_alert_policy(alert_policy)

		self.assertEqual(len(pm.alert_policies), 2)

	def test_policies_by_tag(self):

		pm = PoliciesManager(self.pdm)

		for alert_policy in config["alert_policies"]:
			pm.add_alert_policy(alert_policy)

		test_policies = pm.policies_by_tags(["test"])
		self.assertEqual(len(test_policies), 2)

		test1_policies = pm.policies_by_tags(["test1"])
		self.assertEqual(len(test1_policies), 1)
		self.assertEqual(test1_policies[0].id, 111111)

		test2_policies = pm.policies_by_tags(["test2"])
		self.assertEqual(len(test2_policies), 1)
		self.assertEqual(test2_policies[0].id, 111111)

		test1_and_test2_policies = pm.policies_by_tags(["test1", "test2"])
		self.assertEqual(len(test1_and_test2_policies), 2)


class TestPolicy(unittest.TestCase):

	def setUp(self):
		self.pdm = MockPolicyDataManager()

	def test_register_server(self):

		policy = Policy(self.pdm, config["alert_policies"][0])
		policy.initialise()

		policy.register_server(all_servers[0])
		for condition in policy.cm.conditions:
			self.assertIn(str(all_servers[0]["id"]), condition)

	def test_deregister_servers(self):
		policy = Policy(self.pdm, config["alert_policies"][0])
		policy.initialise()
	
		policy.register_server(all_servers[0])
		policy.register_server(all_servers[1])

		result = policy.deregister_servers([all_servers[0]])
		for condition in policy.cm.conditions:
			self.assertNotIn(str(all_servers[1]["id"]), condition.entities)