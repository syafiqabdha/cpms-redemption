from fastapi.testclient import TestClient


def test_openapi_json_schema(client: TestClient):
    """Verify OpenAPI specification matches expected routes and schemas."""
    response = client.get("/openapi.json")
    assert response.status_code == 200
    spec = response.json()

    # Verify OpenAPI version and basic info
    assert spec.get("openapi", "").startswith("3.")
    assert "info" in spec
    assert "paths" in spec

    # Verify system status endpoint path
    paths = spec["paths"]
    assert "/api/v1/system/status" in paths
    assert "get" in paths["/api/v1/system/status"]

    system_get = paths["/api/v1/system/status"]["get"]
    assert system_get["operationId"] == "getSystemStatus"
    assert "200" in system_get["responses"]

    # Verify redemptions endpoint path exists
    assert "/api/v1/redemptions" in paths
    assert "post" in paths["/api/v1/redemptions"]
    assert "/api/v1/redemptions/{id}/status" in paths
