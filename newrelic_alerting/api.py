from flask import Blueprint, jsonify
from . import run

api = Blueprint("api", __name__)

@api.route("/synchronise")
def synchronise():
    try:
        run.main_app()
    except Exception as re:
        response = jsonify(re.to_dict())
        response.status_code = 503
        return response
    return jsonify({"status": 200, "message": "OK"})