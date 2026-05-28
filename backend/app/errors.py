from flask import jsonify


class AppError(Exception):
    status_code = 400

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.message = message

        if status_code:
            self.status_code = status_code


class UnauthorizedError(AppError):
    status_code = 401


class NotFoundError(AppError):
    status_code = 404


class ValidationError(AppError):
    status_code = 400


def register_error_handlers(app):
    @app.errorhandler(AppError)
    def handle_app_error(error):
        return jsonify({"error": error.message}), error.status_code

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        return jsonify({"error": "Internal server error"}), 500
