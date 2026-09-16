from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient

from app.schemas.system import SystemStatusResponse
from app.services.holiday_service import HolidayService, get_holiday_service


def test_system_status_endpoint_contract(client: TestClient):
    """Verify GET /api/v1/system/status adheres strictly to OpenAPI contract."""
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200

    data = response.json()
    assert "is_operational" in data
    assert isinstance(data["is_operational"], bool)
    assert "server_time_sgt" in data
    assert isinstance(data["server_time_sgt"], str)
    assert "is_weekday" in data
    assert isinstance(data["is_weekday"], bool)
    assert "is_public_holiday" in data
    assert isinstance(data["is_public_holiday"], bool)
    assert "holiday_name" in data
    assert data["holiday_name"] is None or isinstance(data["holiday_name"], str)

    # Validate header propagation
    assert "x-request-id" in response.headers

    # Validate schema parsing with Pydantic
    parsed = SystemStatusResponse(**data)
    assert parsed.server_time_sgt.endswith("+08:00") or "+08:00" in parsed.server_time_sgt


def test_operating_window_evaluation(holiday_service: HolidayService):
    """Test operating hours window (12:00–15:00 UTC+8) on standard weekdays."""
    sgt = ZoneInfo("Asia/Singapore")

    # Inside operating window: Wednesday 12:30 SGT
    dt_inside = datetime(2026, 9, 16, 12, 30, 0, tzinfo=sgt)
    status_inside = holiday_service.check_operating_status(dt_inside)
    assert status_inside.is_operational is True
    assert status_inside.is_weekday is True
    assert status_inside.is_public_holiday is False
    assert status_inside.holiday_name is None

    # Window boundary: 12:00:00 SGT
    dt_start = datetime(2026, 9, 16, 12, 0, 0, tzinfo=sgt)
    assert holiday_service.check_operating_status(dt_start).is_operational is True

    # Window boundary: 15:00:00 SGT
    dt_end = datetime(2026, 9, 16, 15, 0, 0, tzinfo=sgt)
    assert holiday_service.check_operating_status(dt_end).is_operational is True

    # Before operating window: Wednesday 11:59:59 SGT
    dt_early = datetime(2026, 9, 16, 11, 59, 59, tzinfo=sgt)
    status_early = holiday_service.check_operating_status(dt_early)
    assert status_early.is_operational is False
    assert status_early.is_weekday is True

    # After operating window: Wednesday 15:00:01 SGT
    dt_late = datetime(2026, 9, 16, 15, 0, 1, tzinfo=sgt)
    status_late = holiday_service.check_operating_status(dt_late)
    assert status_late.is_operational is False
    assert status_late.is_weekday is True


def test_weekend_evaluation(holiday_service: HolidayService):
    """Verify Saturday and Sunday are rejected as non-operational."""
    sgt = ZoneInfo("Asia/Singapore")

    # Saturday during lunch hours
    dt_sat = datetime(2026, 9, 19, 13, 0, 0, tzinfo=sgt)
    status_sat = holiday_service.check_operating_status(dt_sat)
    assert status_sat.is_operational is False
    assert status_sat.is_weekday is False

    # Sunday during lunch hours
    dt_sun = datetime(2026, 9, 20, 13, 0, 0, tzinfo=sgt)
    status_sun = holiday_service.check_operating_status(dt_sun)
    assert status_sun.is_operational is False
    assert status_sun.is_weekday is False


def test_singapore_public_holiday_evaluation(holiday_service: HolidayService):
    """Verify Singapore gazetted public holidays reject operational status even on weekdays."""
    sgt = ZoneInfo("Asia/Singapore")

    # Good Friday 2026 (Friday April 3, 2026 at 13:00)
    dt_gf = datetime(2026, 4, 3, 13, 0, 0, tzinfo=sgt)
    status_gf = holiday_service.check_operating_status(dt_gf)
    assert status_gf.is_operational is False
    assert status_gf.is_weekday is True
    assert status_gf.is_public_holiday is True
    assert status_gf.holiday_name == "Good Friday"

    # Labour Day 2026 (Friday May 1, 2026 at 12:30)
    dt_labour = datetime(2026, 5, 1, 12, 30, 0, tzinfo=sgt)
    status_labour = holiday_service.check_operating_status(dt_labour)
    assert status_labour.is_operational is False
    assert status_labour.is_public_holiday is True
    assert status_labour.holiday_name == "Labour Day"

    # National Day in lieu (Monday Aug 10, 2026 at 14:00)
    dt_nd = datetime(2026, 8, 10, 14, 0, 0, tzinfo=sgt)
    status_nd = holiday_service.check_operating_status(dt_nd)
    assert status_nd.is_operational is False
    assert status_nd.is_public_holiday is True
    assert status_nd.holiday_name == "National Day (in lieu)"


def test_dependency_injection_override(client: TestClient):
    """Verify FastAPI dependency override works smoothly for testing and external mocking."""
    from app.main import app

    class MockHolidayService(HolidayService):
        def check_operating_status(self, dt=None):
            return SystemStatusResponse(
                is_operational=True,
                server_time_sgt="2026-09-16T12:30:00+08:00",
                is_weekday=True,
                is_public_holiday=False,
                holiday_name=None,
            )

    app.dependency_overrides[get_holiday_service] = MockHolidayService
    try:
        response = client.get("/api/v1/system/status")
        assert response.status_code == 200
        data = response.json()
        assert data["is_operational"] is True
        assert data["server_time_sgt"] == "2026-09-16T12:30:00+08:00"
    finally:
        app.dependency_overrides.clear()
