import os
from flask import Flask
from flask_cors import CORS

def create_app():
    # Отримуємо абсолютний шлях до кореня проєкту
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))

    frontend_dist = os.path.join(BASE_DIR, "frontend", "dist")

    app = Flask(
        __name__,
        static_folder=frontend_dist,
        static_url_path="/"
    )

    app.secret_key = "super-secret"
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = False

    CORS(app, supports_credentials=True)

    from backend.app.routes import main
    app.register_blueprint(main)

    return app