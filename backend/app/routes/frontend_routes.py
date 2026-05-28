from flask import Blueprint

from backend.app.routes.common import *

frontend_bp = Blueprint("frontend", __name__)


# ---------------------------
# REACT
# ---------------------------


@frontend_bp.route("/", defaults={"path": ""})
@frontend_bp.route("/<path:path>")
def serve_react(path):
    if path.startswith("api/") or path.startswith("auth/"):
        return jsonify({"error": "Not found"}), 404

    return current_app.send_static_file("index.html")
