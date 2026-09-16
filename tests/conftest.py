import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.holiday_service import HolidayService


@pytest.fixture
def client():
    """Yield a FastAPI TestClient instance."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def holiday_service():
    """Return a fresh HolidayService instance."""
    return HolidayService()
