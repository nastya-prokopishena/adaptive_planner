from flask import Blueprint, current_app, jsonify

frontend_bp = Blueprint("frontend", __name__)


# ---------------------------
# REACT
# ---------------------------


@frontend_bp.route("/", defaults={"path": ""}, methods=["GET"])
@frontend_bp.route("/<path:path>", methods=["GET"])
def serve_react(path):
    if path.startswith(("api/", "auth/")):
        return jsonify({"error": "Not found"}), 404

    return current_app.send_static_file("index.html")
