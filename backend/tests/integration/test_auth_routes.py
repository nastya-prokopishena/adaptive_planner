import pytest


@pytest.mark.integration
def test_register_requires_email_and_password(client):
    response = client.post("/auth/register", json={})

    assert response.status_code in {400, 422}
    assert "error" in response.get_json()


@pytest.mark.integration
def test_login_requires_valid_credentials(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code in {401, 400, 500}
    assert response.is_json
