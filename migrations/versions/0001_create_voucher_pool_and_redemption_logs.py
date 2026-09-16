"""create voucher_pool and redemption_logs

Revision ID: 0001
Revises: None
Create Date: 2026-09-16 07:30:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema to revision 0001."""
    # Ensure pgcrypto or native gen_random_uuid extension is available
    op.execute(sa.text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))

    # 1. CPMS Voucher Inventory Pool
    op.create_table(
        "voucher_pool",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("voucher_code", sa.String(length=32), nullable=False),
        sa.Column("batch_id", sa.String(length=32), server_default="DEFAULT_BATCH", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="AVAILABLE", nullable=False),
        sa.Column("issued_to_vehicle_hash", sa.String(length=64), nullable=True),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_voucher_pool"),
        sa.UniqueConstraint("voucher_code", name="uq_voucher_pool_voucher_code"),
        sa.CheckConstraint(
            "status IN ('AVAILABLE', 'ISSUED', 'REDEEMED', 'EXPIRED', 'REVOKED')",
            name="ck_voucher_pool_status",
        ),
    )

    # Crucial: Partial Index for O(1) FIFO lock-free allocation
    op.create_index(
        "idx_voucher_pool_fifo_available",
        "voucher_pool",
        ["id"],
        unique=False,
        postgresql_where=sa.text("status = 'AVAILABLE'"),
    )
    op.create_index(
        "idx_voucher_pool_batch_id",
        "voucher_pool",
        ["batch_id"],
        unique=False,
    )
    op.create_index(
        "idx_voucher_pool_expires_at",
        "voucher_pool",
        ["expires_at"],
        unique=False,
        postgresql_where=sa.text("status = 'ISSUED'"),
    )

    # 2. Audit & Redemption Log
    op.create_table(
        "redemption_logs",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("vehicle_plate_hash", sa.String(length=64), nullable=False),
        sa.Column("receipt_hash", sa.String(length=64), nullable=False),
        sa.Column("merchant_name", sa.String(length=100), nullable=False),
        sa.Column("receipt_amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("receipt_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("voucher_code_issued", sa.String(length=32), nullable=False),
        sa.Column(
            "redemption_date",
            sa.Date(),
            server_default=sa.text("CURRENT_DATE"),
            nullable=False,
        ),
        sa.Column(
            "verification_mode",
            sa.String(length=20),
            server_default="AI_AUTO",
            nullable=False,
        ),
        sa.Column("confidence_score", sa.Numeric(precision=4, scale=3), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_redemption_logs"),
        sa.UniqueConstraint("receipt_hash", name="uq_redemption_logs_receipt_hash"),
        sa.ForeignKeyConstraint(
            ["voucher_code_issued"],
            ["voucher_pool.voucher_code"],
            name="fk_redemption_logs_voucher_code",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "verification_mode IN ('AI_AUTO', 'MANUAL_STAFF')",
            name="ck_redemption_logs_verification_mode",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0.000 AND confidence_score <= 1.000",
            name="ck_redemption_logs_confidence_score",
        ),
    )

    # Strict unique constraint: 1 redemption per vehicle per calendar day
    op.create_index(
        "uq_redemption_vehicle_daily",
        "redemption_logs",
        ["vehicle_plate_hash", "redemption_date"],
        unique=True,
    )
    # Audit log chronological querying
    op.create_index(
        "idx_redemption_logs_created_at",
        "redemption_logs",
        [sa.text("created_at DESC")],
        unique=False,
    )
    # Foreign key join index
    op.create_index(
        "idx_redemption_logs_voucher_code",
        "redemption_logs",
        ["voucher_code_issued"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade database schema from revision 0001."""
    # Drop redemption_logs indexes and table first
    op.drop_index("idx_redemption_logs_voucher_code", table_name="redemption_logs")
    op.drop_index("idx_redemption_logs_created_at", table_name="redemption_logs")
    op.drop_index("uq_redemption_vehicle_daily", table_name="redemption_logs")
    op.drop_table("redemption_logs")

    # Drop voucher_pool indexes and table
    op.drop_index("idx_voucher_pool_expires_at", table_name="voucher_pool")
    op.drop_index("idx_voucher_pool_batch_id", table_name="voucher_pool")
    op.drop_index("idx_voucher_pool_fifo_available", table_name="voucher_pool")
    op.drop_table("voucher_pool")
