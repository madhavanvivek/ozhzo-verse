from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.infrastructure.database.session import get_db
from src.infrastructure.cache.redis_client import get_redis_client

router = APIRouter(tags=["Health"])

APP_VERSION = "0.1.0-pilot.1"


@router.get("/health/live", status_code=status.HTTP_200_OK)
async def liveness():
    return {
        "status": "ok",
        "service": "ozhzo-verse-api",
        "version": APP_VERSION
    }


@router.get("/health/ready")
async def readiness(
    db: AsyncSession = Depends(get_db),
    redis_client: redis.Redis = Depends(get_redis_client),
):
    checks = {"database": "unknown", "cache": "unknown"}
    is_healthy = True

    # 1. Database check
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "up"
    except Exception as e:
        checks["database"] = f"down ({str(e)})"
        is_healthy = False

    # 2. Redis check
    try:
        await redis_client.ping()
        checks["cache"] = "up"
    except Exception as e:
        checks["cache"] = f"down ({str(e)})"
        is_healthy = False

    status_code = status.HTTP_200_OK if is_healthy else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "healthy" if is_healthy else "degraded",
            "version": APP_VERSION,
            "checks": checks
        },
    )
