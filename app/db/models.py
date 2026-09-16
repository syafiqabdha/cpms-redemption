from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class VoucherStatus(StrEnum):
    """Lifecycle states for CPMS vouchers."""

    AVAILABLE = "AVAILABLE"
    ISSUED = "ISSUED"
    REDEEMED = "REDEEMED"
    EXPIRED = "EXPIRED"
    REVOKED = "REVOKED"


class VerificationMode(StrEnum):
    """Mode of verification for redemption audit logging."""

    AI_AUTO = "AI_AUTO"
    MANUAL_STAFF = "MANUAL_STAFF"


class VoucherPool(Base):
    """
    CPMS Voucher Inventory Pool.

    Stores pre-authorized CPMS voucher codes available for atomic FIFO allocation.
    Includes partial index `idx_voucher_pool_fifo_available` for O(1) lock-free allocation.
    """

    __tablename__ = "voucher_pool"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    voucher_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    batch_id: Mapped[str] = mapped_column(
        String(32), nullable=False, default="DEFAULT_BATCH", server_default="DEFAULT_BATCH"
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VoucherStatus.AVAILABLE.value,
        server_default=VoucherStatus.AVAILABLE.value,
    )
    issued_to_vehicle_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    redemption_logs: Mapped[list["RedemptionLog"]] = relationship(
        "RedemptionLog", back_populates="voucher", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "status IN ('AVAILABLE', 'ISSUED', 'REDEEMED', 'EXPIRED', 'REVOKED')",
            name="ck_voucher_pool_status",
        ),
        # Crucial: Partial Index for O(1) FIFO lock-free allocation
        Index(
            "idx_voucher_pool_fifo_available",
            "id",
            postgresql_where=text("status = 'AVAILABLE'"),
        ),
        Index("idx_voucher_pool_batch_id", "batch_id"),
        Index(
            "idx_voucher_pool_expires_at",
            "expires_at",
            postgresql_where=text("status = 'ISSUED'"),
        ),
    )


class RedemptionLog(Base):
    """
    Audit & Redemption Log.

    Records successful and staff-approved redemptions.
    Enforces strict 1-redemption-per-vehicle-per-calendar-day constraint
    via unique index `uq_redemption_vehicle_daily`.
    """

    __tablename__ = "redemption_logs"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )
    vehicle_plate_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    receipt_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    merchant_name: Mapped[str] = mapped_column(String(100), nullable=False)
    receipt_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    receipt_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    voucher_code_issued: Mapped[str] = mapped_column(
        String(32),
        ForeignKey("voucher_pool.voucher_code", ondelete="RESTRICT"),
        nullable=False,
    )
    redemption_date: Mapped[date] = mapped_column(
        Date, nullable=False, server_default=func.current_date()
    )
    verification_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=VerificationMode.AI_AUTO.value,
        server_default=VerificationMode.AI_AUTO.value,
    )
    confidence_score: Mapped[Decimal] = mapped_column(Numeric(4, 3), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    voucher: Mapped["VoucherPool"] = relationship("VoucherPool", back_populates="redemption_logs")

    __table_args__ = (
        # Strict unique index: 1 redemption per vehicle per calendar day
        Index(
            "uq_redemption_vehicle_daily",
            "vehicle_plate_hash",
            "redemption_date",
            unique=True,
        ),
        # Audit query and 72h retention pruning index
        Index("idx_redemption_logs_created_at", text("created_at DESC")),
        # Foreign key join index
        Index("idx_redemption_logs_voucher_code", "voucher_code_issued"),
        CheckConstraint(
            "verification_mode IN ('AI_AUTO', 'MANUAL_STAFF')",
            name="ck_redemption_logs_verification_mode",
        ),
        CheckConstraint(
            "confidence_score >= 0.000 AND confidence_score <= 1.000",
            name="ck_redemption_logs_confidence_score",
        ),
    )
