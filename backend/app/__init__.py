from flask import Flask
from flask_cors import CORS
import os


def create_app():
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path=""
    )

    app.secret_key = os.getenv("SECRET_KEY", "super_secret_key_123")

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

    from backend.app.routes import main
    app.register_blueprint(main)

    print("APP CREATED")
    print("STATIC PATH:", app.static_folder)

    return app