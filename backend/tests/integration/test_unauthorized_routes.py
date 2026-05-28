import pytest


@pytest.mark.integration
def test_events_require_authorization(client):
    response = client.get("/api/events")

    assert response.status_code == 401
    assert "error" in response.get_json()


@pytest.mark.integration
def test_tasks_require_authorization(client):
    response = client.get("/api/tasks")

    assert response.status_code == 401
    assert "error" in response.get_json()


@pytest.mark.integration
def test_analytics_require_authorization(client):
    response = client.get("/api/analytics/dashboard")

    assert response.status_code == 401
    assert "error" in response.get_json()
