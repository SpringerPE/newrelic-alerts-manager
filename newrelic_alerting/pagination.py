import requests
from . import helper

logger = helper.getLogger(__name__)

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
        except requests.exceptions.RequestException as e:
            logger.error(str(e))
            raise(e)

def entities(url, session, entity_name, params=None):
    entities = []
    for response in pages(url, session, params=params):
        json_response = response.json()
        if entity_name in json_response:
            entities[0:0] = json_response[entity_name]
    return entities

class handle_response(object):

    def __init__(self, f):
        self.f = f

    def __call__(self, *args, **kwargs):
        try:
            response = self.f(*args, **kwargs)
            if response.status_code != 200:
                logger.error("Expected status 200 got {status}".format(status=response.status_code))
                return False
        except requests.exceptions.RequestException as re:
            logger.error(str(re))
            return False
        return True

    def __get__(self, instance, owner):
        from functools import partial
        return partial(self.__call__, instance)
