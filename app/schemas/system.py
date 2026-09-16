from pydantic import BaseModel, ConfigDict, Field


class SystemStatusResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "is_operational": True,
                "server_time_sgt": "2026-09-16T12:30:00+08:00",
                "is_weekday": True,
                "is_public_holiday": False,
                "holiday_name": None,
            }
        }
    )

    is_operational: bool = Field(
        ...,
        description=(
            "Whether system is currently active for parking redemption "
            "(weekday, 12:00-15:00 SGT, non-holiday)"
        ),
        json_schema_extra={"example": True},
    )
    server_time_sgt: str = Field(
        ...,
        description="Current server time in Singapore Timezone (UTC+8)",
        json_schema_extra={"example": "2026-09-16T12:30:00+08:00"},
    )
    is_weekday: bool = Field(
        ...,
        description="Whether today is a weekday (Monday-Friday in SGT)",
        json_schema_extra={"example": True},
    )
    is_public_holiday: bool = Field(
        ...,
        description="Whether today is a gazetted Singapore public holiday",
        json_schema_extra={"example": False},
    )
    holiday_name: str | None = Field(
        default=None,
        description="Name of the Singapore public holiday if applicable, else null",
        json_schema_extra={"example": None},
    )
