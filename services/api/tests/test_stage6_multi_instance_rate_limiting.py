import pytest
from unittest.mock import AsyncMock
from src.core.rate_limiter import RedisDistributedRateLimiter, InMemoryRateLimiter


@pytest.mark.asyncio
async def test_two_api_instances_share_redis_rate_limit_state():
    """
    MULTI-INSTANCE REDIS RATE LIMITING PROOF:
    API Instance A and API Instance B share identical state via Redis.
    Neither instance allows quota bypass by switching targets.
    """
    # Shared state backend simulating Redis cluster
    redis_storage = {"hits": 0, "is_online": True}

    mock_redis = AsyncMock()

    async def mock_eval(script, numkeys, key, now, window_start, limit, ttl, salt):
        if not redis_storage["is_online"]:
            raise ConnectionError("Redis cluster unreachable")
        redis_storage["hits"] += 1
        current = redis_storage["hits"]
        if current <= limit:
            return [1, limit - current, 0]
        else:
            return [0, 0, 60]

    mock_redis.eval.side_effect = mock_eval

    # Two distinct API server instances
    api_instance_a = RedisDistributedRateLimiter()
    api_instance_b = RedisDistributedRateLimiter()

    client_key = "user-session:999"
    limit = 3

    # Step 1: Instance A processes Request 1
    allowed1, rem1, _ = await api_instance_a.is_allowed(client_key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed1 is True
    assert rem1 == 2

    # Step 2: Instance B processes Request 2
    allowed2, rem2, _ = await api_instance_b.is_allowed(client_key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed2 is True
    assert rem2 == 1

    # Step 3: Instance A processes Request 3 (hitting limit)
    allowed3, rem3, _ = await api_instance_a.is_allowed(client_key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed3 is True
    assert rem3 == 0

    # Step 4: Client tries to bypass limit by switching to Instance B (Request 4)
    allowed4, rem4, retry_after = await api_instance_b.is_allowed(client_key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed4 is False
    assert rem4 == 0
    assert retry_after == 60  # Blocked globally across both instances!

    # Step 5: Simulate Instance A and Instance B Restarts (new process instantiation)
    api_instance_a_restarted = RedisDistributedRateLimiter()
    api_instance_b_restarted = RedisDistributedRateLimiter()

    # Even after pod restarts, Redis maintains the rate limit boundary
    allowed5, _, _ = await api_instance_a_restarted.is_allowed(client_key, limit=limit, window_seconds=60, redis_client=mock_redis)
    assert allowed5 is False

    # Step 6: Simulate Redis Outage
    redis_storage["is_online"] = False
    new_client = "user-session:1001"

    # Instance A falls back gracefully to in-memory limiter without throwing 500
    allowed_fallback, _, _ = await api_instance_a_restarted.is_allowed(new_client, limit=5, window_seconds=60, redis_client=mock_redis)
    assert allowed_fallback is True

    # Step 7: Restore Redis
    redis_storage["is_online"] = True
    redis_storage["hits"] = 0

    # Instance B resumes Redis-backed distributed limiting seamlessly
    allowed_recovered, rem_rec, _ = await api_instance_b_restarted.is_allowed(new_client, limit=5, window_seconds=60, redis_client=mock_redis)
    assert allowed_recovered is True
    assert rem_rec == 4
