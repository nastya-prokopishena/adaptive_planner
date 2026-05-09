from flask import Flask
from flask_cors import CORS
import os

def create_app():
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
    frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")

    app = Flask(
        __name__,
        static_folder=frontend_dist,
        static_url_path="/"
    )

    app.secret_key = "super_secret_key_123"

    app.config["SESSION_COOKIE_NAME"] = "session"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_COOKIE_DOMAIN"] = None

    CORS(app, supports_credentials=True)

    from backend.app.routes import main
    app.register_blueprint(main)

    print("APP CREATED")
    print("STATIC PATH:", frontend_dist)

    return app