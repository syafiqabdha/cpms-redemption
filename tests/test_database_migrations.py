import os
import shutil
import subprocess
import sys

import pytest

from app.db.base import Base
from app.db.migration_runner import (
    get_alembic_config,
    get_sql_migration_path,
    read_sql_migration,
)
from app.db.models import (
    VerificationMode,
    VoucherStatus,
)


def test_sql_migration_files_exist():
    """Verify that both raw up and down DDL SQL migration files exist."""
    up_path = get_sql_migration_path("0001_create_voucher_pool_and_redemption_logs.up.sql")
    down_path = get_sql_migration_path("0001_create_voucher_pool_and_redemption_logs.down.sql")

    assert up_path.is_file(), f"Up migration file missing: {up_path}"
    assert down_path.is_file(), f"Down migration file missing: {down_path}"


def test_sql_migration_content_and_indexes():
    """Verify that up.sql contains required tables, constraints, and specific indexes."""
    up_sql = read_sql_migration("0001_create_voucher_pool_and_redemption_logs.up.sql")
    down_sql = read_sql_migration("0001_create_voucher_pool_and_redemption_logs.down.sql")

    # Tables
    assert "CREATE TABLE IF NOT EXISTS voucher_pool" in up_sql
    assert "CREATE TABLE IF NOT EXISTS redemption_logs" in up_sql

    # Required partial index: idx_voucher_pool_fifo_available WHERE status = 'AVAILABLE'
    assert "idx_voucher_pool_fifo_available" in up_sql
    assert "WHERE status = 'AVAILABLE'" in up_sql

    # Required unique index: uq_redemption_vehicle_daily
    assert "uq_redemption_vehicle_daily" in up_sql
    assert "ON redemption_logs (vehicle_plate_hash, redemption_date)" in up_sql

    # Created at index
    assert "idx_redemption_logs_created_at" in up_sql
    assert "ON redemption_logs (created_at DESC)" in up_sql

    # Foreign key
    expected_fk = "voucher_code_issued VARCHAR(32) NOT NULL REFERENCES voucher_pool(voucher_code)"
    assert expected_fk in up_sql

    # Constraints
    assert "ck_voucher_pool_status" in up_sql
    assert "ck_redemption_logs_verification_mode" in up_sql
    assert "ck_redemption_logs_confidence_score" in up_sql

    # Down SQL drops
    assert "DROP TABLE IF EXISTS redemption_logs" in down_sql
    assert "DROP TABLE IF EXISTS voucher_pool" in down_sql
    assert "idx_voucher_pool_fifo_available" in down_sql
    assert "uq_redemption_vehicle_daily" in down_sql


def test_alembic_config_and_offline_generation():
    """Verify Alembic can parse configuration and compile PostgreSQL DDL offline."""
    cfg = get_alembic_config()
    assert cfg is not None

    # Run alembic upgrade head --sql offline via CLI
    res_up = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head", "--sql"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "CREATE TABLE voucher_pool" in res_up.stdout
    assert "CREATE TABLE redemption_logs" in res_up.stdout
    assert "idx_voucher_pool_fifo_available" in res_up.stdout
    assert "uq_redemption_vehicle_daily" in res_up.stdout

    # Run alembic downgrade 0001:base --sql offline via CLI
    res_down = subprocess.run(
        [sys.executable, "-m", "alembic", "downgrade", "0001:base", "--sql"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "DROP TABLE redemption_logs" in res_down.stdout
    assert "DROP TABLE voucher_pool" in res_down.stdout


def test_sqlalchemy_orm_models_reflection():
    """Verify SQLAlchemy ORM models conform to the schema specifications."""
    # Check tables in Base.metadata
    assert "voucher_pool" in Base.metadata.tables
    assert "redemption_logs" in Base.metadata.tables

    vp_table = Base.metadata.tables["voucher_pool"]
    assert "id" in vp_table.c
    assert "voucher_code" in vp_table.c
    assert "batch_id" in vp_table.c
    assert "status" in vp_table.c
    assert "issued_to_vehicle_hash" in vp_table.c
    assert "issued_at" in vp_table.c
    assert "expires_at" in vp_table.c
    assert "created_at" in vp_table.c

    # Check partial index on voucher_pool
    fifo_index = next(
        (idx for idx in vp_table.indexes if idx.name == "idx_voucher_pool_fifo_available"), None
    )
    assert fifo_index is not None, "idx_voucher_pool_fifo_available index not found on VoucherPool"
    assert fifo_index.dialect_options["postgresql"]["where"] is not None

    rl_table = Base.metadata.tables["redemption_logs"]
    assert "id" in rl_table.c
    assert "vehicle_plate_hash" in rl_table.c
    assert "receipt_hash" in rl_table.c
    assert "merchant_name" in rl_table.c
    assert "receipt_amount" in rl_table.c
    assert "receipt_timestamp" in rl_table.c
    assert "voucher_code_issued" in rl_table.c
    assert "redemption_date" in rl_table.c
    assert "verification_mode" in rl_table.c
    assert "confidence_score" in rl_table.c
    assert "created_at" in rl_table.c

    # Check unique index on redemption_logs
    daily_index = next(
        (idx for idx in rl_table.indexes if idx.name == "uq_redemption_vehicle_daily"), None
    )
    assert daily_index is not None, "uq_redemption_vehicle_daily index not found on RedemptionLog"
    assert daily_index.unique is True

    # Check enums
    assert VoucherStatus.AVAILABLE.value == "AVAILABLE"
    assert VoucherStatus.ISSUED.value == "ISSUED"
    assert VerificationMode.AI_AUTO.value == "AI_AUTO"
    assert VerificationMode.MANUAL_STAFF.value == "MANUAL_STAFF"


@pytest.fixture(scope="module")
def postgres_test_container():
    """
    Spins up an ephemeral PostgreSQL 16 container for live migration testing
    if Docker is available.
    """
    if not shutil.which("docker"):
        pytest.skip("Docker is not installed on the system.")

    container_name = "test-cpms-pg-s1-05"
    port = "55433"
    db_name = "cpms_test_db"
    user = "cpms_user"
    password = "cpms_password"

    # Stop any leftover container with the same name
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    # Start PostgreSQL 16 container
    run_cmd = [
        "docker",
        "run",
        "-d",
        "--rm",
        "--name",
        container_name,
        "-e",
        f"POSTGRES_DB={db_name}",
        "-e",
        f"POSTGRES_USER={user}",
        "-e",
        f"POSTGRES_PASSWORD={password}",
        "-p",
        f"{port}:5432",
        "postgres:16-alpine",
    ]
    res = subprocess.run(run_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        pytest.skip(f"Could not start docker container: {res.stderr}")

    # Wait for PostgreSQL to complete initial setup and accept TCP connections
    import socket
    import time

    ready = False
    for _ in range(50):
        logs = subprocess.run(
            ["docker", "logs", container_name],
            capture_output=True,
            text=True,
        )
        combined_logs = (logs.stdout or "") + (logs.stderr or "")
        if (
            "ready for start up." in combined_logs
            and combined_logs.count("database system is ready to accept connections") >= 2
        ):
            try:
                with socket.create_connection(("127.0.0.1", int(port)), timeout=1):
                    ready = True
                    break
            except OSError:
                pass
        time.sleep(0.3)

    if not ready:
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        pytest.skip("PostgreSQL container failed to become ready in time.")

    db_url = f"postgresql+asyncpg://{user}:{password}@127.0.0.1:{port}/{db_name}"
    yield {"container_name": container_name, "db_url": db_url, "port": port}

    # Teardown
    subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)


@pytest.mark.asyncio
async def test_live_postgres_migrations_e2e(postgres_test_container):
    """
    Perform end-to-end verification against a real PostgreSQL 16 instance:
    1. Apply up SQL migration.
    2. Verify indexes in PostgreSQL pg_indexes catalog.
    3. Test constraints: unique daily redemption per vehicle, unique voucher code,
       foreign keys, and check constraints.
    4. Apply down SQL migration and verify tables are dropped.
    5. Run Alembic upgrade head and downgrade base against live PostgreSQL.
    """
    import asyncpg

    container = postgres_test_container
    conn_url = container["db_url"].replace("postgresql+asyncpg://", "postgresql://")

    # 1. Connect and execute up SQL
    up_sql = read_sql_migration("0001_create_voucher_pool_and_redemption_logs.up.sql")
    conn = await asyncpg.connect(conn_url)
    try:
        await conn.execute(up_sql)

        # 2. Inspect pg_indexes catalog
        indexes = await conn.fetch(
            """
            SELECT tablename, indexname, indexdef
            FROM pg_indexes
            WHERE schemaname = 'public'
            ORDER BY indexname;
            """
        )
        index_map = {row["indexname"]: row for row in indexes}

        # Verify idx_voucher_pool_fifo_available partial index
        assert "idx_voucher_pool_fifo_available" in index_map
        fifo_def = index_map["idx_voucher_pool_fifo_available"]["indexdef"]
        assert "WHERE" in fifo_def and "status" in fifo_def and "AVAILABLE" in fifo_def

        # Verify uq_redemption_vehicle_daily unique index
        assert "uq_redemption_vehicle_daily" in index_map
        daily_def = index_map["uq_redemption_vehicle_daily"]["indexdef"]
        assert "UNIQUE INDEX" in daily_def
        assert "vehicle_plate_hash" in daily_def
        assert "redemption_date" in daily_def

        # 3. Test Data & Constraints
        # Insert a valid voucher
        await conn.execute(
            """
            INSERT INTO voucher_pool (voucher_code, batch_id, status)
            VALUES ('V-TEST-001', 'BATCH-01', 'AVAILABLE');
            """
        )

        # Duplicate voucher_code must fail
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                """
                INSERT INTO voucher_pool (voucher_code, batch_id, status)
                VALUES ('V-TEST-001', 'BATCH-02', 'AVAILABLE');
                """
            )

        # Invalid status must fail check constraint
        with pytest.raises(asyncpg.CheckViolationError):
            await conn.execute(
                """
                INSERT INTO voucher_pool (voucher_code, batch_id, status)
                VALUES ('V-TEST-002', 'BATCH-01', 'INVALID_STATUS');
                """
            )

        # Insert redemption log
        await conn.execute(
            """
            INSERT INTO redemption_logs (
                vehicle_plate_hash,
                receipt_hash,
                merchant_name,
                receipt_amount,
                receipt_timestamp,
                voucher_code_issued,
                redemption_date,
                verification_mode,
                confidence_score
            ) VALUES (
                'hash_plate_sg1234',
                'hash_receipt_001',
                'Toast Box',
                35.50,
                NOW(),
                'V-TEST-001',
                CURRENT_DATE,
                'AI_AUTO',
                0.985
            );
            """
        )

        # Duplicate redemption per vehicle on the same calendar day MUST FAIL
        # (Testing uq_redemption_vehicle_daily)
        await conn.execute(
            """
            INSERT INTO voucher_pool (voucher_code, batch_id, status)
            VALUES ('V-TEST-002', 'BATCH-01', 'AVAILABLE');
            """
        )
        with pytest.raises(asyncpg.UniqueViolationError):
            await conn.execute(
                """
                INSERT INTO redemption_logs (
                    vehicle_plate_hash,
                    receipt_hash,
                    merchant_name,
                    receipt_amount,
                    receipt_timestamp,
                    voucher_code_issued,
                    redemption_date,
                    verification_mode,
                    confidence_score
                ) VALUES (
                    'hash_plate_sg1234', -- Same vehicle plate hash
                    'hash_receipt_002', -- Different receipt
                    'Din Tai Fung',
                    50.00,
                    NOW(),
                    'V-TEST-002',
                    CURRENT_DATE,        -- Same calendar date
                    'AI_AUTO',
                    0.950
                );
                """
            )

        # FK constraint failure on non-existent voucher code
        with pytest.raises(asyncpg.ForeignKeyViolationError):
            await conn.execute(
                """
                INSERT INTO redemption_logs (
                    vehicle_plate_hash,
                    receipt_hash,
                    merchant_name,
                    receipt_amount,
                    receipt_timestamp,
                    voucher_code_issued,
                    confidence_score
                ) VALUES (
                    'hash_plate_sg9999',
                    'hash_receipt_003',
                    'Din Tai Fung',
                    50.00,
                    NOW(),
                    'NON_EXISTENT_VOUCHER',
                    0.950
                );
                """
            )

        # 4. Apply down SQL migration
        down_sql = read_sql_migration("0001_create_voucher_pool_and_redemption_logs.down.sql")
        await conn.execute(down_sql)

        # Verify tables are dropped
        tables = await conn.fetch(
            """
            SELECT tablename FROM pg_tables
            WHERE schemaname = 'public';
            """
        )
        table_names = [r["tablename"] for r in tables]
        assert "voucher_pool" not in table_names
        assert "redemption_logs" not in table_names

    finally:
        await conn.close()

    # 5. Test Alembic live upgrade & downgrade
    env = os.environ.copy()
    env["DATABASE_URL"] = container["db_url"]

    # Upgrade with alembic
    subprocess.run(
        [".venv/bin/alembic", "upgrade", "head"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    # Check tables created by alembic
    conn2 = await asyncpg.connect(conn_url)
    try:
        tables2 = await conn2.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        table_names2 = [r["tablename"] for r in tables2]
        assert "voucher_pool" in table_names2
        assert "redemption_logs" in table_names2
        assert "alembic_version" in table_names2
    finally:
        await conn2.close()

    # Downgrade with alembic
    subprocess.run(
        [".venv/bin/alembic", "downgrade", "base"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    conn3 = await asyncpg.connect(conn_url)
    try:
        tables3 = await conn3.fetch("SELECT tablename FROM pg_tables WHERE schemaname = 'public';")
        table_names3 = [r["tablename"] for r in tables3]
        assert "voucher_pool" not in table_names3
        assert "redemption_logs" not in table_names3
    finally:
        await conn3.close()
