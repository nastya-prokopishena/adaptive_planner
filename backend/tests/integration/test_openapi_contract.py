def test_swagger_or_openapi_page_available(client):
    possible_urls = [
        "/swagger",
        "/apidocs",
        "/openapi.json",
        "/docs",
    ]

    responses = [client.get(url) for url in possible_urls]

    assert any(response.status_code in [200, 301, 302] for response in responses)
