from fastapi.testclient import TestClient


def test_cors_preflight_options(client: TestClient):
    """Verify CORS preflight OPTIONS request returns required headers."""
    headers = {
        "Origin": "https://shopper.pancatz.com",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Request-ID,Content-Type",
    }
    response = client.options("/api/v1/system/status", headers=headers)
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers
    assert response.headers.get("access-control-allow-origin") == "*"
    assert "access-control-allow-methods" in response.headers


def test_cors_simple_get(client: TestClient):
    """Verify CORS headers on standard GET request."""
    headers = {
        "Origin": "https://shopper.pancatz.com",
    }
    response = client.get("/api/v1/system/status", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "*"
    assert "access-control-expose-headers" in response.headers
    assert "x-request-id" in response.headers.get("access-control-expose-headers").lower()
