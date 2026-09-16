import json
import logging

from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.core.logging import StructuredJSONFormatter, set_request_id
from app.main import app


def test_request_id_header_propagation(client: TestClient):
    """Ensure X-Request-ID is preserved when passed by client."""
    custom_id = "req-custom-trace-9999"
    response = client.get("/api/v1/system/status", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id


def test_request_id_header_auto_generation(client: TestClient):
    """Ensure a UUID X-Request-ID is generated when omitted by client."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    req_id = response.headers.get("X-Request-ID")
    assert req_id is not None
    assert len(req_id) >= 16


def test_structured_json_formatter():
    """Verify StructuredJSONFormatter outputs valid JSON with expected schema."""
    formatter = StructuredJSONFormatter()
    set_request_id("ctx-trace-12345")

    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=42,
        msg="Test event occurred",
        args=(),
        exc_info=None,
    )
    record.extra_field = "custom_value"

    output = formatter.format(record)
    parsed = json.loads(output)

    assert parsed["level"] == "INFO"
    assert parsed["logger"] == "test_logger"
    assert parsed["message"] == "Test event occurred"
    assert parsed["request_id"] == "ctx-trace-12345"
    assert parsed["extra_field"] == "custom_value"
    assert "timestamp" in parsed


def test_unhandled_exception_handling():
    """Verify unhandled exceptions return 500 JSON response with error_code."""
    test_router = APIRouter()

    @test_router.get("/error-trigger-route")
    async def error_route():
        raise RuntimeError("Simulated crash in endpoint")

    app.include_router(test_router, prefix="/api/v1")

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get(
            "/api/v1/error-trigger-route",
            headers={"X-Request-ID": "err-trace-1"},
        )
        assert response.status_code == 500
        assert response.headers.get("X-Request-ID") == "err-trace-1"
        data = response.json()
        assert data["error_code"] == "INTERNAL_SERVER_ERROR"
        assert "message" in data
