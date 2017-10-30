from flask import Blueprint, jsonify
from flask import current_app as app

import traceback
from . import run
from . import helper

logger = helper.getLogger(__name__)

api = Blueprint("api", __name__)

@api.route("/synchronise", methods = ['POST'])
def synchronise():
    try:
        run.run_synch(app.config)
    except Exception as re:
        logger.error(re)
        logger.error(repr(traceback.format_stack()))
        response = jsonify({
            "error": str(re)
        })
        response.status_code = 503
        return response
    return jsonify({"status": 200, "message": "OK"})