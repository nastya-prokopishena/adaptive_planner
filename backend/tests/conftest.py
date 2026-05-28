import os
import sys
from pathlib import Path

import pytest

# Робимо корінь проєкту доступним для імпортів backend.*
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Безпечні тестові env-змінні, щоб сервіси не падали під час імпорту.
os.environ.setdefault("FLASK_ENV", "testing")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("OPENAI_SCHEDULE_MODEL", "gpt-4o-mini")
os.environ.setdefault("GOOGLE_CLIENT_SECRET_FILE", "backend/infrastructure/credentials.json")
os.environ.setdefault("GOOGLE_REDIRECT_URI", "http://localhost:5000/callback")
os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")


@pytest.fixture
def app():
    from backend.app import create_app

    app = create_app()
    app.config.update(
        TESTING=True,
        SECRET_KEY="test-secret-key",
        WTF_CSRF_ENABLED=False,
    )
    return app


@pytest.fixture
def client(app):
    return app.test_client()
