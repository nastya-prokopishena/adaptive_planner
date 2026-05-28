from backend.application.auth_service import AuthService


def test_password_hash_and_check_work():
    password = "StrongPassword123"

    hashed = AuthService.hash_password(password)

    assert hashed != password
    assert AuthService.check_password(password, hashed) is True
    assert AuthService.check_password("wrong", hashed) is False
