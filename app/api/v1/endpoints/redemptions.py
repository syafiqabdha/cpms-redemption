from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.schemas.error import ErrorResponse, ReceiptValidationErrorResponse
from app.schemas.redemption import (
    ManualReviewQueuedResponse,
    RedemptionSuccessResponse,
    ReviewStatusResponse,
)

router = APIRouter()


@router.post(
    "/redemptions",
    summary="Submit receipt and vehicle plate for autonomous redemption",
    description=(
        "Ingests an uploaded receipt image and Singapore vehicle plate number, "
        "evaluates eligibility via Multimodal Vision AI, and atomically allocates "
        "a Code 128 barcode voucher."
    ),
    operation_id="submitRedemption",
    responses={
        200: {
            "model": RedemptionSuccessResponse,
            "description": "Redemption auto-approved and voucher allocated.",
        },
        202: {
            "model": ManualReviewQueuedResponse,
            "description": (
                "Routed to staff manual review queue (e.g., borderline confidence or glare flag)."
            ),
        },
        400: {
            "model": ErrorResponse,
            "description": "Invalid vehicle plate format or missing parameters.",
        },
        409: {
            "model": ErrorResponse,
            "description": "Daily limit reached or receipt already redeemed.",
        },
        422: {
            "model": ReceiptValidationErrorResponse,
            "description": (
                "Receipt validation failed (below spend threshold, outside hours, invalid tenant)."
            ),
        },
        503: {
            "model": ErrorResponse,
            "description": "Voucher pool exhausted or system out of operating hours.",
        },
    },
)
async def submit_redemption(
    receipt_image: UploadFile = File(..., description="Receipt photo (JPEG, PNG, WebP; max 10MB)"),
    vehicle_plate: str = Form(
        ..., description="Singapore vehicle license plate number (e.g. SBA1234A)"
    ),
):
    """
    Scaffolded endpoint for autonomous redemption submission.
    Business logic and multimodal pipeline will be hooked in CPMS-S1-06 / CPMS-S2-01.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Redemption pipeline implementation in progress (Sprint 1 / Sprint 2 tickets).",
    )


@router.get(
    "/redemptions/{id}/status",
    summary="Poll status of a queued manual review",
    operation_id="getRedemptionStatus",
    responses={
        200: {
            "model": ReviewStatusResponse,
            "description": "Current review state",
        }
    },
)
async def get_redemption_status(id: UUID):
    """
    Scaffolded endpoint for polling manual review status.
    Will be hooked to Redis / Postgres review queue in CPMS-S2-06 / CPMS-S3-04.
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Review status lookup implementation in progress.",
    )
