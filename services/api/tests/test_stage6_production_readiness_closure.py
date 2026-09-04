import os
import time
import uuid
import sqlite3
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.backup_recovery import BackupRecoveryManager, BackupMetadata, RestoreResult
from src.core.rate_limiter import RedisDistributedRateLimiter, InMemoryRateLimiter
from src.infrastructure.jobs.background_job_manager import BackgroundJobManager
from src.infrastructure.database.models import (
    BackgroundJobModel,
    PaymentTransactionModel,
    SubscriptionModel,
    UserModel,
    HomeModel,
    HomeMemberModel,
    TaskModel,
    HouseholdMemoryModel
)
from src.services.automation_engine import AutomationEngine
from src.api.v1.payments import handle_payment_webhook


# ==============================================================================
# 1. BACKUP & DISASTER RECOVERY TEST (ACTUAL RESTORE & INTEGRITY CHECK)
# ==============================================================================

def test_actual_database_backup_and_restore_cycle():
    staging_dir = "/tmp/ozhzo_dr_test"
    os.makedirs(staging_dir, exist_ok=True)
    source_db = os.path.join(staging_dir, "source_prod.db")
    restore_target_db = os.path.join(staging_dir, "restored_prod.db")
    backup_vault = os.path.join(staging_dir, "backups")

    if os.path.exists(source_db):
        os.remove(source_db)
    if os.path.exists(restore_target_db):
        os.remove(restore_target_db)

    # 1. Create source schema & known test data
    conn = sqlite3.connect(source_db)
    cursor = conn.cursor()
    cursor.executescript("""
        CREATE TABLE users (id TEXT PRIMARY KEY, email TEXT, role TEXT);
        CREATE TABLE homes (id TEXT PRIMARY KEY, name TEXT);
        CREATE TABLE home_members (id TEXT PRIMARY KEY, home_id TEXT, user_id TEXT, role TEXT, FOREIGN KEY(home_id) REFERENCES homes(id), FOREIGN KEY(user_id) REFERENCES users(id));
        CREATE TABLE tasks (id TEXT PRIMARY KEY, home_id TEXT, title TEXT, status TEXT, FOREIGN KEY(home_id) REFERENCES homes(id));
        CREATE TABLE household_memories (id TEXT PRIMARY KEY, home_id TEXT, category TEXT, content TEXT, status TEXT);
    """)

    # Insert sample records
    u_id = str(uuid.uuid4())
    h_id = str(uuid.uuid4())
    cursor.execute("INSERT INTO users VALUES (?, ?, ?);", (u_id, "admin@ozhzo.com", "OWNER"))
    cursor.execute("INSERT INTO homes VALUES (?, ?);", (h_id, "Highland Manor"))
    cursor.execute("INSERT INTO home_members VALUES (?, ?, ?, ?);", (str(uuid.uuid4()), h_id, u_id, "OWNER"))
    cursor.execute("INSERT INTO tasks VALUES (?, ?, ?, ?);", (str(uuid.uuid4()), h_id, "Inspect Water Heater", "TODO"))
    cursor.execute("INSERT INTO household_memories VALUES (?, ?, ?, ?, ?);", (str(uuid.uuid4()), h_id, "ROUTINE", "Trash pickup on Tuesdays", "ACTIVE"))
    conn.commit()
    conn.close()

    # 2. Perform automated encrypted backup
    encryption_key = "ozhzo-secure-disaster-recovery-key-2026"
    meta = BackupRecoveryManager.create_database_backup(
        source_db_path=source_db,
        backup_dir=backup_vault,
        encryption_key=encryption_key
    )
    assert meta.total_records == 5
    assert meta.is_encrypted is True
    assert os.path.exists(meta.backup_file_path)

    # 3. Validate backup integrity & checksum
    is_valid = BackupRecoveryManager.verify_backup_integrity(
        meta.backup_file_path,
        meta.sha256_checksum,
        encryption_key=encryption_key
    )
    assert is_valid is True

    # 4. Simulate complete source loss / corruption
    os.remove(source_db)
    assert not os.path.exists(source_db)

    # 5. Execute isolated restore into target DB
    restore_res: RestoreResult = BackupRecoveryManager.restore_database_backup(
        backup_file_path=meta.backup_file_path,
        target_db_path=restore_target_db,
        metadata=meta,
        encryption_key=encryption_key
    )

    # 6. Verify restore results & measured RTO
    assert restore_res.status == "COMPLETED"
    assert restore_res.integrity_check_passed is True
    assert restore_res.foreign_keys_valid is True
    assert restore_res.total_records_verified == 5
    assert restore_res.tables_restored == 5
    assert restore_res.duration_seconds < 5.0  # RTO under 5 seconds

    # 7. Smoke test data consistency on restored DB
    r_conn = sqlite3.connect(restore_target_db)
    r_cursor = r_conn.cursor()
    r_cursor.execute("SELECT name FROM homes WHERE id = ?;", (h_id,))
    assert r_cursor.fetchone()[0] == "Highland Manor"
    r_cursor.execute("SELECT title FROM tasks WHERE home_id = ?;", (h_id,))
    assert r_cursor.fetchone()[0] == "Inspect Water Heater"
    r_conn.close()


# ==============================================================================
# 2. REDIS DISTRIBUTED RATE LIMITER & CROSS-INSTANCE CONSISTENCY
# ==============================================================================

@pytest.mark.asyncio
async def test_redis_distributed_rate_limiter_cross_instance_consistency():
    # Mock Redis client with stateful evaluation
    mock_redis = AsyncMock()
    # Simulate Redis Lua execution returning [allowed, remaining, retry_after]
    call_counts = {"count": 0}

    async def mock_eval(script, numkeys, key, now, window_start, limit, ttl, salt):
        call_counts["count"] += 1
        if call_counts["count"] <= limit:
            return [1, limit - call_counts["count"], 0]
        else:
            return [0, 0, 45]

    mock_redis.eval.side_effect = mock_eval

    limiter_instance_a = RedisDistributedRateLimiter()
    limiter_instance_b = RedisDistributedRateLimiter()

    key = "ip:198.51.100.25"
    limit = 2

    # Instance A consumes 1
    allowed1, rem1, _ = await limiter_instance_a.is_allowed(key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed1 is True
    assert rem1 == 1

    # Instance B sees shared state and consumes 1
    allowed2, rem2, _ = await limiter_instance_b.is_allowed(key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed2 is True
    assert rem2 == 0

    # Instance A attempts 3rd request -> Blocked across cluster
    allowed3, rem3, retry_after = await limiter_instance_a.is_allowed(key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed3 is False
    assert rem3 == 0
    assert retry_after == 45


@pytest.mark.asyncio
async def test_redis_failure_graceful_fallback():
    # Redis raises ConnectionError -> Limiter must fall back to in-memory gracefully without raising 500
    mock_redis = AsyncMock()
    mock_redis.eval.side_effect = ConnectionError("Redis cluster unreachable")

    limiter = RedisDistributedRateLimiter()
    key = "ip:203.0.113.50"

    allowed, remaining, _ = await limiter.is_allowed(key, limit=5, window_seconds=60, redis_client=mock_redis)
    assert allowed is True
    assert remaining == 4


# ==============================================================================
# 3. DISTRIBUTED BACKGROUND WORKER CRASH RECOVERY
# ==============================================================================

@pytest.mark.asyncio
async def test_background_worker_crash_and_zombie_job_reclamation():
    mock_db = AsyncMock()
    home_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Job stuck in RUNNING from a crashed Worker A (lock acquired 60 seconds ago)
    zombie_job = BackgroundJobModel(
        id=uuid.uuid4(),
        job_type="NOTIFICATION_DISPATCH",
        home_id=home_id,
        payload={"title": "Test notification"},
        status="RUNNING",
        locked_by="worker-A-crashed",
        locked_at=now - timedelta(seconds=60),  # Stale lock
        retry_count=0,
        max_retries=3,
        next_run_at=now - timedelta(seconds=60),
        created_at=now - timedelta(seconds=70),
        updated_at=now - timedelta(seconds=60),
    )

    # Worker B inspects due jobs with lock_timeout_seconds=30
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [zombie_job]))

    results = await BackgroundJobManager.process_due_jobs(
        db=mock_db, worker_id="worker-B-active", limit=1, lock_timeout_seconds=30
    )

    # Worker B successfully reclaimed the zombie job and executed to COMPLETED
    assert len(results) == 1
    assert results[0]["status"] == "COMPLETED"
    assert zombie_job.status == "COMPLETED"
    assert zombie_job.locked_by == "worker-B-active"


# ==============================================================================
# 4. AUTOMATION DISTRIBUTED EXECUTION & TIME-BUCKETED RECURRING SAFETY
# ==============================================================================

def test_automation_scheduler_reliability_and_timezone_stability():
    automation_id = uuid.uuid4()

    # Trigger payload with explicit UTC hour bucket
    event_morning_utc = {"id": "bill-electric", "time_bucket": "2026-09-02T08:00:00Z"}
    key1 = AutomationEngine.generate_idempotency_key(automation_id, "SCHEDULED_TIME", event_morning_utc)

    # Same morning event processed by Worker B at 08:00 -> Identical key (deduplicated)
    key1_worker_b = AutomationEngine.generate_idempotency_key(automation_id, "SCHEDULED_TIME", event_morning_utc)
    assert key1 == key1_worker_b

    # Next recurring cycle next day at 08:00 -> Different key (executes reliably)
    event_next_day = {"id": "bill-electric", "time_bucket": "2026-09-03T08:00:00Z"}
    key2 = AutomationEngine.generate_idempotency_key(automation_id, "SCHEDULED_TIME", event_next_day)
    assert key1 != key2


# ==============================================================================
# 5. PAYMENT WEBHOOK ADVERSARIAL RESILIENCE (REPLAY & SIGNATURES)
# ==============================================================================

@pytest.mark.asyncio
async def test_payment_webhook_idempotency_and_replay_protection():
    mock_db = AsyncMock()
    tx_id = uuid.uuid4()
    user_id = uuid.uuid4()
    home_id = uuid.uuid4()

    # Pre-existing SUCCESS transaction (already processed)
    existing_tx = PaymentTransactionModel(
        id=tx_id,
        user_id=user_id,
        home_id=home_id,
        provider="MOCK",
        provider_transaction_id="pay_mock_9999",
        idempotency_key="pay_mock_9999",
        status="SUCCESS",
        amount=19.99,
        currency="USD"
    )

    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(first=lambda: existing_tx))

    # Replay webhook delivery
    mock_request = AsyncMock()
    mock_request.body.return_value = b'{"provider_transaction_id": "pay_mock_9999", "status": "SUCCESS"}'

    with patch("src.api.v1.payments.get_payment_provider") as mock_provider_factory:
        mock_provider = AsyncMock()
        mock_provider.provider_name = "MOCK"
        mock_provider.handle_webhook.return_value = {
            "valid": True,
            "provider_transaction_id": "pay_mock_9999",
            "status": "SUCCESS"
        }
        mock_provider_factory.return_value = mock_provider

        resp = await handle_payment_webhook(
            provider_name="MOCK",
            request=mock_request,
            db=mock_db,
            x_signature="mock_valid_sig"
        )

        # Idempotency guard returned already_processed without modifying subscription
        assert resp["status"] == "already_processed"
        assert resp["transaction_id"] == str(tx_id)
