from flask import Flask
from flask_cors import CORS

from backend.config import get_config
from backend.app.errors import register_error_handlers


def create_app():
    app = Flask(
        __name__,
        static_folder="../static",
        static_url_path=""
    )

    app.config.from_object(get_config())

    CORS(
        app,
        supports_credentials=True,
        origins=app.config["CORS_ALLOWED_ORIGINS"]
    )

    from backend.app.routes.auth_routes import auth_bp
    from backend.app.routes.event_routes import event_bp
    from backend.app.routes.task_routes import task_bp
    from backend.app.routes.schedule_import_routes import schedule_import_bp
    from backend.app.routes.analytics_routes import analytics_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(schedule_import_bp)
    app.register_blueprint(analytics_bp)

    register_error_handlers(app)

    return app