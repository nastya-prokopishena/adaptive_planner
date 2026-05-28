from backend.app import create_app


def test_session_cookie_is_httponly():
    app = create_app()

    assert app.config["SESSION_COOKIE_HTTPONLY"] is True


def test_secret_key_is_not_empty():
    app = create_app()

    assert app.config["SECRET_KEY"]
    assert app.config["SECRET_KEY"] != ""
