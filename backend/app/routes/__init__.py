from backend.app.routes.analytics_routes import analytics_bp
from backend.app.routes.auth_routes import auth_bp
from backend.app.routes.event_routes import event_bp
from backend.app.routes.frontend_routes import frontend_bp
from backend.app.routes.schedule_import_routes import schedule_import_bp
from backend.app.routes.task_routes import task_bp


def register_routes(app):
    app.register_blueprint(auth_bp)
    app.register_blueprint(event_bp)
    app.register_blueprint(task_bp)
    app.register_blueprint(schedule_import_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(frontend_bp)
