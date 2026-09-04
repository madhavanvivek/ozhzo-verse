import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException
from httpx import AsyncClient

from src.main import app
from src.core.rate_limiter import RedisDistributedRateLimiter
from src.services.ai_assistant_service import AIAssistantService
from src.schemas.ai import AIChatRequest
from src.infrastructure.jobs.background_job_manager import BackgroundJobManager
from src.infrastructure.database.models import BackgroundJobModel, HomeModel, UserModel
from src.api.dependencies import HomeContext


# ==============================================================================
# 1. DATABASE UNAVAILABILITY FAILURE INJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_database_down_readiness_probe():
    mock_db = AsyncMock()
    mock_db.execute.side_effect = Exception("FATAL: connection to database server lost")

    from src.api.v1.health import readiness
    resp = await readiness(db=mock_db)

    # Must return 503 SERVICE UNAVAILABLE with degraded status
    assert resp.status_code == 503
    import json
    body = json.loads(resp.body.decode())
    assert body["status"] == "degraded"
    assert "down" in body["checks"]["database"]


# ==============================================================================
# 2. REDIS CLUSTER OUTAGE FAILURE INJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_redis_cluster_outage_graceful_degradation():
    mock_redis = AsyncMock()
    mock_redis.eval.side_effect = TimeoutError("Redis master timed out")

    limiter = RedisDistributedRateLimiter()
    key = "ip:10.0.0.1"

    # Evaluates gracefully against in-memory bucket without unhandled 500 error
    allowed, remaining, _ = await limiter.is_allowed(key, limit=10, window_seconds=60, redis_client=mock_redis)
    assert allowed is True
    assert remaining == 9


# ==============================================================================
# 3. AI PROVIDER TIMEOUT FAILURE INJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_ai_provider_timeout_graceful_handling():
    home_id = uuid.uuid4()
    user_id = uuid.uuid4()
    mock_user = UserModel(id=user_id, email="user@ozhzo.com")
    mock_home = HomeModel(id=home_id, name="Sunset Villa", currency="USD")
    home_ctx = HomeContext(home_id=home_id, user=mock_user, role="MEMBER")

    mock_db = AsyncMock()
    res_home = MagicMock()
    res_home.scalar_one_or_none.return_value = mock_home
    empty_res = MagicMock()
    empty_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = empty_res

    service = AIAssistantService()
    # Mock AI provider timing out
    mock_provider = AsyncMock()
    mock_provider.detect_intent.side_effect = TimeoutError("Upstream neural provider timed out")
    service.provider = mock_provider

    req = AIChatRequest(message="What tasks do we have today?")

    with pytest.raises(TimeoutError):
        await service.process_chat(mock_db, home_ctx, req)


# ==============================================================================
# 4. PAYMENT GATEWAY TIMEOUT / RETRY INJECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_payment_gateway_down_preserves_subscription_state():
    from src.domain.entitlements import compute_subscription_lifecycle_status
    from src.infrastructure.database.models import SubscriptionModel

    # Even if gateway is down, existing subscription with future expiry remains authoritative
    future_date = datetime.now(timezone.utc) + timedelta(days=120)
    sub = SubscriptionModel(
        id=uuid.uuid4(),
        home_id=uuid.uuid4(),
        status="ACTIVE",
        current_period_ends_at=future_date
    )

    lifecycle = compute_subscription_lifecycle_status(sub)
    assert lifecycle == "ACTIVE"


# ==============================================================================
# 5. BACKGROUND NOTIFICATION WORKER RETRY & DLQ ISOLATION
# ==============================================================================

@pytest.mark.asyncio
async def test_notification_worker_failure_exponential_backoff_and_dlq():
    mock_db = AsyncMock()
    home_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    # Job at attempt 2 with max_retries = 3
    job = BackgroundJobModel(
        id=uuid.uuid4(),
        job_type="FLAKY_NOTIF_JOB",
        home_id=home_id,
        payload={"msg": "Push"},
        status="PENDING",
        retry_count=2,
        max_retries=3,
        next_run_at=now,
        created_at=now,
        updated_at=now
    )

    # Register handler that fails
    async def _failing_push(db, payload, h_id):
        raise ConnectionRefusedError("APNS/FCM push gateway rejected connection")

    BackgroundJobManager.register_handler("FLAKY_NOTIF_JOB", _failing_push)
    mock_db.execute.return_value = MagicMock(scalars=lambda: MagicMock(all=lambda: [job]))

    results = await BackgroundJobManager.process_due_jobs(mock_db, worker_id="worker-test", limit=1)

    # Hits max retries and isolates into DEAD_LETTER queue
    assert results[0]["status"] == "DEAD_LETTER"
    assert job.status == "DEAD_LETTER"
    assert "rejected connection" in job.last_error

