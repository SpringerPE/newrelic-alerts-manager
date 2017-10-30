# newrelic-alerts-manager

`newrelic-alerts-manager` is a simple utility which allows to dynamically update the newrelic server alerting
policies based on the value of some specific tags added to them.

The code is compatible with Python 3

Documentation of the APIs used:

* https://docs.newrelic.com/docs/apis

#INSTALLATION

## Example

Install via pip: `pip install newrelic-alerts-manager`

## Upload to PyPI

1. Create a `.pypirc` configuration file. This file holds your information for authenticating with PyPI.

   ```
   [distutils]
   index-servers = pypi

   [pypi]
   repository=https://pypi.python.org/pypi
   username=your_username
   password=your_password
   ```
2. Login and upload it to PyPI

   ```
   python setup.py register -r pypi
   python setup.py sdist upload -r pypi
   ```

#USAGE

##ALERT_CONFIG configuration


#####example configuration:
```

alert_policies:
  - name: "Alert Policy LIVE"
    tags:
    - live-web
    - live-backend
  - name: "Alert Policy DEV"
    tags:
    - dev-web
    - dev-database

```

the `ALERT_CONFIG` configuration is a `yaml` formatted document, containing an array of `alert_policies`. 
Each alert policy is identified by its newrelic name and contains a list of server tags 
([newrelic labels](https://docs.newrelic.com/docs/data-analysis/user-interface-functions/organize-your-data/labels-categories-organize-apps-servers-monitors)) listing the servers
associated with it (with all its conditions).

The only supported server label is currently `Deployment`. Therefore ie., according to the configuration above,
the only servers associated with the `Alert Policy LIVE` would be those labelled in newrelic with one or both of the 
`Deployment:live-web` and `Deployment:live-backend` server labels.

##Running as a web app



##Running on Cloudfoundry

When running on Cloudfoundry you will need a properly formatted application manifest. One example manifest can
be found below, as well as in the `manifest-example.yml` file:
```
applications:
- name: newrelic-alerts-manager
  memory: 128M
  instances: 1
  env:
    NEWRELIC_API_KEY: <your_secret_new_relic_key>
    ALERT_CONFIG: |
      ---
      alert_policies:
          - name: "Alert Policy LIVE"
            tags:
            - live-web
            - live-backend
          - name: "Alert Policy DEV"
            tags:
            - dev-web
            - dev-database

```

in this case the alert configuration is passed to the app in the form of an online yaml document.

The `NEWRELIC_API_KEY` variable can be either specified in the manifest itself or binding your app to a
newrelic service, created via a service broker ie. using [newrelic-cf](https://github.com/newrelic/newrelic-cf).

In this case the key is expected to be found under the `VCAP_SERVICES["newrelic"][0]["credentials"]["licenseKey"]`
dictionary key.

##Running as a script

An alert config file named `alert_config.yml` should be present in the execution directory. An example can be found
at the root of this project in the `alert_config.example.yml` file.

You can specify an alternative configuration file path via the `-c` flag

You can run the utility by executing the run script:

```
./run -k <new_relic_api_key>
```

or after installing the pip package

```
python setup.py install
```

by running

```
newrelic-alerts-manager -k <new_relic_api_key>
```

## Author

Springer Nature Platform Engineering, Claudio Benfatto (claudio.benfatto@springer.com)
