import pytest


def test_swagger_or_openapi_page_available(client):
    possible_urls = [
        "/swagger",
        "/apidocs",
        "/openapi.json",
        "/docs",
    ]

    responses = [client.get(url) for url in possible_urls]

    assert any(response.status_code in [200, 301, 302] for response in responses)


@pytest.mark.integration
def test_openapi_or_swagger_endpoint_is_available(client):
    possible_urls = [
        "/openapi.json",
        "/swagger",
        "/apidocs",
        "/docs",
    ]

    responses = [client.get(url) for url in possible_urls]

    assert any(response.status_code in {200, 301, 302} for response in responses)


@pytest.mark.integration
def test_frontend_api_unknown_route_returns_not_found_json(app):
    from backend.app.routes import frontend_routes

    with app.test_request_context("/api/unknown-route", method="GET"):
        response, status = frontend_routes.serve_react("api/unknown-route")

    assert status == 404
    assert response.is_json
    assert response.get_json()["error"] == "Not found"
