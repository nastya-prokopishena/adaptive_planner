# backend/app/__init__.py

from flask import Flask
from flask_cors import CORS

from backend.app.routes import register_routes
from backend.app.errors import register_error_handlers


def create_app():
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path=""
    )

    app.secret_key = "super_secret_key_123"

    app.config["SESSION_COOKIE_NAME"] = "session"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_PERMANENT"] = True
    app.config["SESSION_COOKIE_DOMAIN"] = None

    CORS(
        app,
        supports_credentials=True,
        origins=[
            "http://localhost:5000",
            "http://127.0.0.1:5000"
        ]
    )

    register_routes(app)
    register_error_handlers(app)

    return app