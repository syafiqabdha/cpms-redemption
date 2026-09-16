from datetime import date, datetime, time
from zoneinfo import ZoneInfo

from app.core.config import settings
from app.schemas.system import SystemStatusResponse

# Baseline Singapore gazetted public holidays (MOM Singapore)
# S1-04 will introduce automated daily sync with data.gov.sg and Redis caching.
SINGAPORE_PUBLIC_HOLIDAYS: dict[date, str] = {
    # 2025
    date(2025, 1, 1): "New Year's Day",
    date(2025, 1, 29): "Chinese New Year",
    date(2025, 1, 30): "Chinese New Year",
    date(2025, 3, 31): "Hari Raya Puasa",
    date(2025, 4, 18): "Good Friday",
    date(2025, 5, 1): "Labour Day",
    date(2025, 5, 12): "Vesak Day",
    date(2025, 6, 7): "Hari Raya Haji",
    date(2025, 8, 9): "National Day",
    date(2025, 10, 20): "Deepavali",
    date(2025, 12, 25): "Christmas Day",
    # 2026
    date(2026, 1, 1): "New Year's Day",
    date(2026, 2, 17): "Chinese New Year",
    date(2026, 2, 18): "Chinese New Year",
    date(2026, 3, 20): "Hari Raya Puasa",
    date(2026, 4, 3): "Good Friday",
    date(2026, 5, 1): "Labour Day",
    date(2026, 5, 27): "Hari Raya Haji",
    date(2026, 5, 31): "Vesak Day",
    date(2026, 6, 1): "Vesak Day (in lieu)",
    date(2026, 8, 9): "National Day",
    date(2026, 8, 10): "National Day (in lieu)",
    date(2026, 11, 8): "Deepavali",
    date(2026, 11, 9): "Deepavali (in lieu)",
    date(2026, 12, 25): "Christmas Day",
}


class HolidayService:
    """Service to evaluate Singapore public holidays and system operating hours."""

    def __init__(self, holidays: dict[date, str] | None = None):
        self._holidays = holidays if holidays is not None else SINGAPORE_PUBLIC_HOLIDAYS
        self._tz = ZoneInfo(settings.OPERATING_TIMEZONE)
        self._start_time = time(settings.OPERATING_START_HOUR, settings.OPERATING_START_MINUTE)
        self._end_time = time(settings.OPERATING_END_HOUR, settings.OPERATING_END_MINUTE)

    def get_holiday_name(self, check_date: date) -> str | None:
        """Return holiday name if date is a Singapore public holiday, else None."""
        return self._holidays.get(check_date)

    def is_public_holiday(self, check_date: date) -> bool:
        """Check if date is a Singapore public holiday."""
        return check_date in self._holidays

    def is_weekday(self, check_date: date) -> bool:
        """Return True if Monday through Friday."""
        return check_date.weekday() < 5

    def is_in_operating_window(self, check_time: time) -> bool:
        """Return True if within operating hours (12:00 - 15:00 SGT)."""
        return self._start_time <= check_time <= self._end_time

    def check_operating_status(self, dt: datetime | None = None) -> SystemStatusResponse:
        """
        Evaluate full system operating status:
        Operational requires: weekday + not public holiday + within 12:00-15:00 SGT.
        """
        if dt is None:
            now_sgt = datetime.now(self._tz)
        else:
            if dt.tzinfo is None:
                now_sgt = dt.replace(tzinfo=self._tz)
            else:
                now_sgt = dt.astimezone(self._tz)

        current_date = now_sgt.date()
        current_time = now_sgt.time()

        weekday = self.is_weekday(current_date)
        holiday_name = self.get_holiday_name(current_date)
        is_holiday = holiday_name is not None
        in_window = self.is_in_operating_window(current_time)

        is_operational = weekday and (not is_holiday) and in_window

        return SystemStatusResponse(
            is_operational=is_operational,
            server_time_sgt=now_sgt.isoformat(),
            is_weekday=weekday,
            is_public_holiday=is_holiday,
            holiday_name=holiday_name,
        )


_holiday_service_instance = HolidayService()


def get_holiday_service() -> HolidayService:
    """Dependency injection provider for HolidayService."""
    return _holiday_service_instance
