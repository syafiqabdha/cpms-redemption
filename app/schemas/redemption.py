from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class RedemptionSuccessResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "APPROVED",
                "voucher_code": "CPMS-99201485",
                "barcode_format": "CODE128",
                "barcode_value": "0001051165",
                "issued_at": "2026-09-16T12:45:10+08:00",
                "expires_at": "2026-09-16T14:45:10+08:00",
                "merchant_name": "Toast Box",
                "eligible_amount": 34.50,
            }
        }
    )

    status: Literal["APPROVED"] = Field(default="APPROVED", description="Redemption outcome status")
    voucher_code: str = Field(..., description="Unique alphanumeric CPMS voucher code")
    barcode_format: str = Field(default="CODE128", description="Barcode encoding standard")
    barcode_value: str = Field(..., description="Numeric gantry barcode payload")
    issued_at: str = Field(..., description="Issuance timestamp (ISO-8601 SGT)")
    expires_at: str = Field(..., description="Voucher expiration timestamp (+2 hours)")
    merchant_name: str = Field(..., description="Validated mall tenant name")
    eligible_amount: float = Field(..., description="Approved eligible receipt amount in SGD")


class ManualReviewQueuedResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "PENDING_REVIEW",
                "review_id": "7e50b4d4-245f-4a0b-936a-2d4e731456a0",
                "message": (
                    "Receipt photo flagged for quick staff verification. "
                    "Please keep this screen open."
                ),
                "estimated_wait_seconds": 45,
            }
        }
    )

    status: Literal["PENDING_REVIEW"] = Field(default="PENDING_REVIEW")
    review_id: UUID = Field(..., description="Unique manual review identifier")
    message: str = Field(..., description="Shopper instruction message")
    estimated_wait_seconds: int = Field(default=45, description="Expected SLA in seconds")


class ReviewStatusResponse(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "APPROVED",
                "voucher_details": {
                    "status": "APPROVED",
                    "voucher_code": "CPMS-99201485",
                    "barcode_format": "CODE128",
                    "barcode_value": "0001051165",
                    "issued_at": "2026-09-16T12:45:10+08:00",
                    "expires_at": "2026-09-16T14:45:10+08:00",
                    "merchant_name": "Toast Box",
                    "eligible_amount": 34.50,
                },
                "rejection_reason": None,
            }
        }
    )

    status: Literal["PENDING_REVIEW", "APPROVED", "REJECTED"] = Field(
        ..., description="Current review status"
    )
    voucher_details: RedemptionSuccessResponse | None = Field(
        default=None, description="Voucher allocation details upon approval"
    )
    rejection_reason: str | None = Field(
        default=None, description="Reason if manual review rejected receipt"
    )
