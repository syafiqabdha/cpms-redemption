from fastapi import APIRouter, Depends

from app.schemas.system import SystemStatusResponse
from app.services.holiday_service import HolidayService, get_holiday_service

router = APIRouter()


@router.get(
    "/system/status",
    response_model=SystemStatusResponse,
    summary="Check system operating status and public holiday gate",
    description=(
        "Returns whether redemption is currently active based on operating hours "
        "(12:00-15:00 UTC+8) and Singapore public holidays."
    ),
    operation_id="getSystemStatus",
    status_code=200,
)
async def get_system_status(
    service: HolidayService = Depends(get_holiday_service),
) -> SystemStatusResponse:
    """Evaluate and return the system's operational health and operating window status."""
    return service.check_operating_status()
