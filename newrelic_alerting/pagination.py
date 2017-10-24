import requests

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

def entities(url, session, entity_name, params=None):
    entities = []
    for response in pages(url, session, params=params):
        json_response = response.json()
        if entity_name in json_response:
            entities[0:0] = json_response[entity_name]
    return entities