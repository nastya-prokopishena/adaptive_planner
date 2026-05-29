def test_tasks_endpoint_requires_authentication(client):
    response = client.get("/api/tasks")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_events_endpoint_requires_authentication(client):
    response = client.get("/api/events")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_analytics_endpoint_requires_authentication(client):
    response = client.get("/api/analytics/dashboard")

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_user_cannot_update_task_without_session(client):
    response = client.put(
        "/api/tasks/1",
        json={"title": "Changed"},
    )

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"


def test_user_cannot_delete_event_without_session(client):
    response = client.delete("/api/events/1", json={})

    assert response.status_code == 401
    assert response.get_json()["error"] == "Unauthorized"
