import os

from flask import Flask
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect

from backend.app.routes import main

csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, static_folder="static", static_url_path="/static")

    app.secret_key = os.getenv("SECRET_KEY", "dev-secret-key")

    csrf.init_app(app)

    CORS(
        app,
        supports_credentials=True,
        origins=["http://localhost:5000", "http://127.0.0.1:5000"],
    )

    app.register_blueprint(main)

    print("APP CREATED")
    print("STATIC PATH:", app.static_folder)

    return app
