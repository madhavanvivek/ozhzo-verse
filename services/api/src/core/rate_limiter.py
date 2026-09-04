import time
import math
import random
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple
from fastapi import HTTPException, Request, status
import redis.asyncio as redis

logger = logging.getLogger("ozhzo.security.ratelimit")

# Atomic sliding-window rate limiting Lua script for Redis
LUA_SLIDING_WINDOW_SCRIPT = """
local key = KEYS[1]
local now = tonumber(ARGV[1])
local window_start = tonumber(ARGV[2])
local limit = tonumber(ARGV[3])
local ttl = tonumber(ARGV[4])
local salt = ARGV[5]

-- 1. Remove elements outside the sliding window
redis.call('ZREMRANGEBYSCORE', key, 0, window_start)

-- 2. Count active hits in current window
local count = redis.call('ZCARD', key)

if count >= limit then
    local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
    local oldest_score = tonumber(oldest[2]) or now
    local retry_after_ms = math.max(1000, (oldest_score + (ttl * 1000)) - now)
    local retry_after = math.ceil(retry_after_ms / 1000)
    return {0, 0, retry_after}
end

-- 3. Record current hit
local member = tostring(now) .. '-' .. salt
redis.call('ZADD', key, now, member)
redis.call('EXPIRE', key, ttl + 5)

local remaining = limit - (count + 1)
return {1, remaining, 0}
"""


class InMemoryRateLimiter:
    """
    In-memory fallback sliding-window rate limiter for standalone execution.
    """

    def __init__(self):
        self._buckets: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, key: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int, float]:
        now = time.time()
        window_start = now - window_seconds

        timestamps = [t for t in self._buckets[key] if t > window_start]
        self._buckets[key] = timestamps

        if len(timestamps) >= limit:
            oldest = timestamps[0]
            retry_after = max(1.0, oldest + window_seconds - now)
            return False, 0, retry_after

        self._buckets[key].append(now)
        remaining = limit - len(self._buckets[key])
        return True, remaining, 0.0


class RedisDistributedRateLimiter:
    """
    Production Redis-backed distributed rate limiter.
    Ensures identical quota visibility across all horizontal server instances (Instance A -> Instance B).
    Gracefully falls back to in-memory rate limiting upon Redis connection timeout.
    """

    def __init__(self, memory_fallback: Optional[InMemoryRateLimiter] = None):
        self.memory_fallback = memory_fallback or InMemoryRateLimiter()
        self._lua_sha: Optional[str] = None

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window_seconds: int = 60,
        redis_client: Optional[redis.Redis] = None,
    ) -> Tuple[bool, int, float]:
        """
        Evaluates sliding window limit atomically in Redis with millisecond precision.
        """
        if not redis_client:
            return self.memory_fallback.is_allowed(key, limit, window_seconds)

        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (window_seconds * 1000)
        redis_key = f"ratelimit:{key}"
        salt = str(random.randint(100000, 999999))

        try:
            result = await redis_client.eval(
                LUA_SLIDING_WINDOW_SCRIPT,
                1,
                redis_key,
                now_ms,
                window_start_ms,
                limit,
                window_seconds,
                salt,
            )
            # result is [allowed (1/0), remaining, retry_after_seconds]
            allowed = bool(result[0])
            remaining = int(result[1])
            retry_after = float(result[2])
            return allowed, remaining, retry_after

        except Exception as e:
            logger.warning(f"Redis distributed rate limit check failed ({e}); failing over to in-memory limiter.")
            return self.memory_fallback.is_allowed(key, limit, window_seconds)

    async def check_async(
        self,
        request: Request,
        route_type: str = "general",
        key_override: Optional[str] = None,
        redis_client: Optional[redis.Redis] = None,
    ) -> None:
        client_ip = request.client.host if request.client else "127.0.0.1"
        key = key_override or f"{route_type}:{client_ip}"

        limits = {
            "auth": (15, 60),      # 15 req/min
            "otp": (5, 60),        # 5 req/min
            "ai": (40, 60),        # 40 req/min
            "general": (180, 60),  # 180 req/min
        }
        limit, window = limits.get(route_type, (180, 60))

        allowed, remaining, retry_after = await self.is_allowed(key, limit, window, redis_client)
        if not allowed:
            logger.warning(f"Distributed rate limit exceeded on {route_type} for key: {key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(int(retry_after))}
            )

    def check(self, request: Request, route_type: str = "general", key_override: Optional[str] = None) -> None:
        """
        Synchronous wrapper using in-memory bucket for sync routes.
        """
        client_ip = request.client.host if request.client else "127.0.0.1"
        key = key_override or f"{route_type}:{client_ip}"

        limits = {
            "auth": (15, 60),
            "otp": (5, 60),
            "ai": (40, 60),
            "general": (180, 60),
        }
        limit, window = limits.get(route_type, (180, 60))

        allowed, remaining, retry_after = self.memory_fallback.is_allowed(key, limit, window)
        if not allowed:
            logger.warning(f"Rate limit exceeded on {route_type} for key: {key}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={"Retry-After": str(int(retry_after))}
            )


rate_limiter = RedisDistributedRateLimiter()
