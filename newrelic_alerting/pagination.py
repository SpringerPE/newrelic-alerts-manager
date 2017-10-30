import requests
import json
from . import helper
from .exceptions import UnexpectedStatusCode

logger = helper.getLogger(__name__)

def handle_response_status(response, expected_status):
    if response.status_code != expected_status:
        text = response.json()
        logger.error("Expected status {expected} got {status} {text}".format(
            expected=expected_status,
            status=response.status_code,
            text=text))
        raise UnexpectedStatusCode(text)

class handle_response(object):

    def __init__(self, f):
        self.f = f

    def __call__(self, *args, **kwargs):
        try:
            response = self.f(*args, **kwargs)
            handle_response_status(response, 200)
        except (requests.exceptions.RequestException, UnexpectedStatusCode) as re:
            logger.error(str(re))
            return None
        return response

    def __get__(self, instance, owner):
        from functools import partial
        return partial(self.__call__, instance)

def pages(url, session, params=None):
    try:
        response = session.get(url, params=params)
        handle_response_status(response, 200)
    except (requests.exceptions.RequestException, UnexpectedStatusCode) as re:
        logger.error("error while getting the paginated response {}".format(str(re)))
        raise StopIteration(re)

    yield response
    while True:
        try:
            next_url = response.links['next']['url']
            response = session.get(next_url)
            handle_response_status(response, 200)
            yield response
        except KeyError:
            break
        except (requests.exceptions.RequestException, UnexpectedStatusCode) as re:
            logger.error(str(re))
            raise StopIteration(re)

def entities(url, session, entity_name, params=None):
    entities = []
    for response in pages(url, session, params=params):
        try:
            json_response = response.json()
            if entity_name in json_response:
                entities[0:0] = json_response[entity_name]
        except json.decoder.JSONDecodeError as je:
            logger.error(str(je))
            break
    return entities


