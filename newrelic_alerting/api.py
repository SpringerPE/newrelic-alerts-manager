from flask import Blueprint, jsonify
import traceback
from . import run
from . import helper

logger = helper.getLogger(__name__)

api = Blueprint("api", __name__)

@api.route("/synchronise")
def synchronise():
    try:
        run.main_app()
    except Exception as re:
        logger.error(re)
        logger.error(repr(traceback.format_stack()))
        response = jsonify({
            "error": str(re)
        })
        response.status_code = 503
        return response
    return jsonify({"status": 200, "message": "OK"})