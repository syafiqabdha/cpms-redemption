-- Migration: 0001_create_voucher_pool_and_redemption_logs
-- Description: Create voucher_pool with FIFO partial index and redemption_logs with daily vehicle constraint
-- Target Database: PostgreSQL 16
-- Reference: docs/architecture/concurrency-and-voucher-pool.md (ARCH-002)

-- Ensure UUID generation is supported
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================================
-- 1. CPMS Voucher Inventory Pool Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS voucher_pool (
    id BIGSERIAL PRIMARY KEY,
    voucher_code VARCHAR(32) UNIQUE NOT NULL,
    batch_id VARCHAR(32) NOT NULL DEFAULT 'DEFAULT_BATCH',
    status VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
    issued_to_vehicle_hash VARCHAR(64),
    issued_at TIMESTAMP WITH TIME ZONE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT ck_voucher_pool_status CHECK (
        status IN ('AVAILABLE', 'ISSUED', 'REDEEMED', 'EXPIRED', 'REVOKED')
    )
);

-- Crucial: Partial Index for O(1) FIFO lock-free allocation
-- Supports the atomic CTE query:
--   SELECT id, voucher_code FROM voucher_pool WHERE status = 'AVAILABLE' ORDER BY id ASC LIMIT 1 FOR UPDATE SKIP LOCKED
CREATE INDEX IF NOT EXISTS idx_voucher_pool_fifo_available 
ON voucher_pool (id ASC) 
WHERE status = 'AVAILABLE';

-- Batch lookup index
CREATE INDEX IF NOT EXISTS idx_voucher_pool_batch_id 
ON voucher_pool (batch_id);

-- Expiration reconciliation index for the 15-minute cron worker:
--   UPDATE voucher_pool SET status = 'EXPIRED' WHERE status = 'ISSUED' AND expires_at < NOW()
CREATE INDEX IF NOT EXISTS idx_voucher_pool_expires_at 
ON voucher_pool (expires_at) 
WHERE status = 'ISSUED';

-- ============================================================================
-- 2. Audit & Redemption Log Table
-- ============================================================================
CREATE TABLE IF NOT EXISTS redemption_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_plate_hash VARCHAR(64) NOT NULL,
    receipt_hash VARCHAR(64) UNIQUE NOT NULL,
    merchant_name VARCHAR(100) NOT NULL,
    receipt_amount NUMERIC(10, 2) NOT NULL,
    receipt_timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    voucher_code_issued VARCHAR(32) NOT NULL REFERENCES voucher_pool(voucher_code) ON DELETE RESTRICT,
    redemption_date DATE NOT NULL DEFAULT CURRENT_DATE,
    verification_mode VARCHAR(20) NOT NULL DEFAULT 'AI_AUTO',
    confidence_score NUMERIC(4, 3) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT ck_redemption_logs_verification_mode CHECK (
        verification_mode IN ('AI_AUTO', 'MANUAL_STAFF')
    ),
    CONSTRAINT ck_redemption_logs_confidence_score CHECK (
        confidence_score >= 0.000 AND confidence_score <= 1.000
    )
);

-- Strict unique constraint: 1 redemption per vehicle per calendar day
-- Catches double-tap submissions and rolls back the atomic allocation CTE
CREATE UNIQUE INDEX IF NOT EXISTS uq_redemption_vehicle_daily 
ON redemption_logs (vehicle_plate_hash, redemption_date);

-- Chronological audit querying and PDPA 72-hour log pruning index
CREATE INDEX IF NOT EXISTS idx_redemption_logs_created_at 
ON redemption_logs (created_at DESC);

-- Foreign key lookup index for joins and integrity checks
CREATE INDEX IF NOT EXISTS idx_redemption_logs_voucher_code 
ON redemption_logs (voucher_code_issued);
