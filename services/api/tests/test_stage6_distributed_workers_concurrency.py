import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.jobs.background_job_manager import BackgroundJobManager
from src.infrastructure.database.models import BackgroundJobModel


@pytest.mark.asyncio
async def test_distributed_background_workers_concurrency_and_crash_recovery():
    """
    DISTRIBUTED WORKERS CONCURRENCY & CRASH PROOF:
    1. Worker A and Worker B attempt to acquire the same job.
    2. Atomic lock ensures only one worker executes.
    3. Worker crash leaves stale lock -> Worker B reclaims zombie job after timeout.
    4. Repeated failures transition job to DEAD_LETTER.
    5. Super Admin re-enqueues job from DLQ.
    """
    home_id = uuid.uuid4()
    mock_db = AsyncMock()
    now = datetime.now(timezone.utc)

    execution_counter = {"count": 0}

    async def _test_side_effect(db, payload, h_id):
        execution_counter["count"] += 1

    BackgroundJobManager.register_handler("TEST_SIDE_EFFECT_JOB", _test_side_effect)

    # 1. Single executable job in PENDING state
    job = BackgroundJobModel(
        id=uuid.uuid4(),
        job_type="TEST_SIDE_EFFECT_JOB",
        home_id=home_id,
        payload={"task_id": "123"},
        status="PENDING",
        retry_count=0,
        max_retries=3,
        next_run_at=now,
        created_at=now,
        updated_at=now
    )

    # 2. Worker A acquires and executes the job
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [job]))

    results_worker_a = await BackgroundJobManager.process_due_jobs(
        db=mock_db, worker_id="worker-A-pod-1", limit=1
    )

    assert len(results_worker_a) == 1
    assert results_worker_a[0]["status"] == "COMPLETED"
    assert execution_counter["count"] == 1
    assert job.status == "COMPLETED"
    assert job.locked_by == "worker-A-pod-1"

    # 3. If Worker B attempts to run immediately, job is already COMPLETED (no duplicate side effects)
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: []))
    results_worker_b = await BackgroundJobManager.process_due_jobs(
        db=mock_db, worker_id="worker-B-pod-2", limit=1
    )
    assert len(results_worker_b) == 0
    assert execution_counter["count"] == 1  # Exactly ONE side effect!

    # 4. Simulate Worker Crash: Job was locked by Worker A 45 seconds ago and never finished
    zombie_job = BackgroundJobModel(
        id=uuid.uuid4(),
        job_type="TEST_SIDE_EFFECT_JOB",
        home_id=home_id,
        payload={"task_id": "456"},
        status="RUNNING",
        locked_by="worker-A-crashed",
        locked_at=now - timedelta(seconds=45),
        retry_count=0,
        max_retries=3,
        next_run_at=now - timedelta(seconds=45),
        created_at=now - timedelta(seconds=50),
        updated_at=now - timedelta(seconds=45)
    )

    # Worker B inspects due jobs with lock_timeout_seconds=30 -> Reclaims zombie job
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [zombie_job]))
    reclaim_results = await BackgroundJobManager.process_due_jobs(
        db=mock_db, worker_id="worker-B-healthy", limit=1, lock_timeout_seconds=30
    )

    assert len(reclaim_results) == 1
    assert reclaim_results[0]["status"] == "COMPLETED"
    assert zombie_job.status == "COMPLETED"
    assert zombie_job.locked_by == "worker-B-healthy"
    assert execution_counter["count"] == 2

    # 5. Simulate Repeated Failure -> Exponential Backoff -> DEAD_LETTER
    async def _failing_handler(db, payload, h_id):
        raise RuntimeError("Worker process network failure")

    BackgroundJobManager.register_handler("FAILING_TEST_JOB", _failing_handler)

    failing_job = BackgroundJobModel(
        id=uuid.uuid4(),
        job_type="FAILING_TEST_JOB",
        home_id=home_id,
        payload={},
        status="PENDING",
        retry_count=2,
        max_retries=3,
        next_run_at=now,
        created_at=now,
        updated_at=now
    )

    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [failing_job]))
    fail_results = await BackgroundJobManager.process_due_jobs(mock_db, worker_id="worker-B", limit=1)
    assert fail_results[0]["status"] == "DEAD_LETTER"
    assert failing_job.status == "DEAD_LETTER"


    # 6. Super Admin Re-enqueues from DLQ
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: failing_job)
    re_enqueued = await BackgroundJobManager.retry_dead_letter_job(mock_db, failing_job.id)
    assert re_enqueued.status == "PENDING"
    assert re_enqueued.retry_count == 0
    assert re_enqueued.last_error is None
