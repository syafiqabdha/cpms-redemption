from pydantic import BaseModel, ConfigDict, Field


class ErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "VEHICLE_DAILY_LIMIT_EXCEEDED",
                "message": "This vehicle plate has already redeemed parking today.",
            }
        }
    )

    error_code: str = Field(
        ...,
        description="Machine-readable error identifier",
        json_schema_extra={"example": "VEHICLE_DAILY_LIMIT_EXCEEDED"},
    )
    message: str = Field(
        ...,
        description="Human-readable error explanation",
        json_schema_extra={"example": "This vehicle plate has already redeemed parking today."},
    )


class ReceiptValidationDetails(BaseModel):
    merchant: str | None = Field(default=None, json_schema_extra={"example": "BreadTalk"})
    receipt_date: str | None = Field(default=None, json_schema_extra={"example": "2026-09-16"})
    receipt_time: str | None = Field(default=None, json_schema_extra={"example": "12:15"})
    gross_total: float | None = Field(default=None, json_schema_extra={"example": 24.80})
    minimum_required: float | None = Field(default=None, json_schema_extra={"example": 30.00})


class ReceiptValidationErrorResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "RECEIPT_INSUFFICIENT_SPEND",
                "message": (
                    "Receipt total of $24.80 is below the required minimum spend of $30.00 SGD."
                ),
                "details": {
                    "merchant": "BreadTalk",
                    "receipt_date": "2026-09-16",
                    "receipt_time": "12:15",
                    "gross_total": 24.80,
                    "minimum_required": 30.00,
                },
            }
        }
    )

    error_code: str = Field(
        ...,
        description="Receipt validation error code",
        json_schema_extra={"example": "RECEIPT_INSUFFICIENT_SPEND"},
    )
    message: str = Field(
        ...,
        description="Human-readable validation message",
        json_schema_extra={
            "example": "Receipt total of $24.80 is below the required minimum spend of $30.00 SGD."
        },
    )
    details: ReceiptValidationDetails | None = Field(
        default=None,
        description="Specific breakdown of failed criteria",
    )
