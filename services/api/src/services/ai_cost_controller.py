import logging
import time
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    AIUsageQuotaModel,
    AIUsageRecordModel,
    HomeModel,
    UserModel
)

logger = logging.getLogger("ozhzo.ai.cost_controller")

# Cost Estimation Constants (USD per 1k tokens)
INPUT_TOKEN_COST_PER_1K = Decimal("0.0015")
OUTPUT_TOKEN_COST_PER_1K = Decimal("0.0020")


class AICostController:
    """
    Production AI Cost Control, Token Tracking, and Home Quota Management.
    Prevents runaway AI spending and provides granular usage telemetry.
    """

    @classmethod
    async def get_or_create_quota(
        cls, db: AsyncSession, home_id: UUID
    ) -> AIUsageQuotaModel:
        now = datetime.now(timezone.utc)
        quota = None
        try:
            stmt = select(AIUsageQuotaModel).where(AIUsageQuotaModel.home_id == home_id)
            res = await db.execute(stmt)
            obj = res.scalar_one_or_none() if hasattr(res, "scalar_one_or_none") else None
            if isinstance(obj, AIUsageQuotaModel):
                quota = obj
        except Exception:
            quota = None

        if not quota or not isinstance(quota, AIUsageQuotaModel):
            quota = AIUsageQuotaModel(
                id=uuid4(),
                home_id=home_id,
                daily_request_limit=100,
                daily_token_limit=100000,
                monthly_cost_limit_usd=Decimal("5.00"),
                current_daily_requests=0,
                current_daily_tokens=0,
                current_monthly_cost_usd=Decimal("0.00"),
                last_daily_reset_at=now,
                last_monthly_reset_at=now,
            )
            try:
                db.add(quota)
                await db.commit()
                await db.refresh(quota)
            except Exception:
                pass
            return quota


        # Daily reset check
        if quota.last_daily_reset_at:
            if (now - quota.last_daily_reset_at) > timedelta(hours=24):
                quota.current_daily_requests = 0
                quota.current_daily_tokens = 0
                quota.last_daily_reset_at = now

        # Monthly reset check
        if quota.last_monthly_reset_at:
            if (now - quota.last_monthly_reset_at) > timedelta(days=30):
                quota.current_monthly_cost_usd = Decimal("0.00")
                quota.last_monthly_reset_at = now

        return quota

    @classmethod
    async def check_quota_before_request(
        cls, db: AsyncSession, home_id: UUID
    ) -> AIUsageQuotaModel:
        """
        Enforces rate/cost limits before processing an AI request.
        """
        quota = await cls.get_or_create_quota(db, home_id)

        if quota.current_daily_requests >= quota.daily_request_limit:
            logger.warning(
                f"AI daily request quota exceeded for home {home_id}: {quota.current_daily_requests}/{quota.daily_request_limit}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "AI_DAILY_QUOTA_EXCEEDED",
                    "message": "Daily AI request limit reached for this household. Quota resets in 24 hours.",
                    "daily_requests": quota.current_daily_requests,
                    "daily_limit": quota.daily_request_limit
                }
            )

        if quota.current_monthly_cost_usd >= quota.monthly_cost_limit_usd:
            logger.warning(
                f"AI monthly budget quota exceeded for home {home_id}: ${quota.current_monthly_cost_usd}/${quota.monthly_cost_limit_usd}"
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "AI_MONTHLY_BUDGET_EXCEEDED",
                    "message": "Monthly AI budget limit reached for this household.",
                    "monthly_cost_usd": str(quota.current_monthly_cost_usd),
                    "monthly_limit_usd": str(quota.monthly_cost_limit_usd)
                }
            )

        return quota

    @classmethod
    async def record_usage(
        cls,
        db: AsyncSession,
        home_id: UUID,
        user_id: UUID,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int,
        provider: str = "mock",
        model_name: str = "ozhzo-neural-v1",
        correlation_id: Optional[str] = None,
        status_str: str = "SUCCESS",
    ) -> AIUsageRecordModel:
        """
        Records structured AI usage telemetry and updates aggregate quota counters.
        """
        total_tokens = prompt_tokens + completion_tokens
        # Calculate estimated cost
        prompt_cost = (Decimal(prompt_tokens) / Decimal(1000)) * INPUT_TOKEN_COST_PER_1K
        completion_cost = (Decimal(completion_tokens) / Decimal(1000)) * OUTPUT_TOKEN_COST_PER_1K
        estimated_cost = prompt_cost + completion_cost

        record = AIUsageRecordModel(
            id=uuid4(),
            home_id=home_id,
            user_id=user_id,
            provider=provider,
            model_name=model_name,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total_tokens,
            estimated_cost_usd=estimated_cost,
            latency_ms=latency_ms,
            status=status_str,
            correlation_id=correlation_id,
            created_at=datetime.now(timezone.utc)
        )
        db.add(record)

        # Update quota aggregates
        quota = await cls.get_or_create_quota(db, home_id)
        quota.current_daily_requests += 1
        quota.current_daily_tokens += total_tokens
        quota.current_monthly_cost_usd += estimated_cost

        await db.commit()
        await db.refresh(record)
        return record

    @classmethod
    async def get_home_ai_telemetry(
        cls, db: AsyncSession, home_id: UUID
    ) -> Dict[str, Any]:
        """
        Fetches 30-day AI consumption metrics for a specific home.
        """
        quota = await cls.get_or_create_quota(db, home_id)

        # Aggregate total requests & tokens in the last 30 days
        since_date = datetime.now(timezone.utc) - timedelta(days=30)
        stmt = (
            select(
                func.count(AIUsageRecordModel.id).label("total_requests"),
                func.coalesce(func.sum(AIUsageRecordModel.total_tokens), 0).label("total_tokens"),
                func.coalesce(func.sum(AIUsageRecordModel.estimated_cost_usd), Decimal("0.00")).label("total_cost"),
                func.coalesce(func.avg(AIUsageRecordModel.latency_ms), 0).label("avg_latency_ms")
            )
            .where(
                AIUsageRecordModel.home_id == home_id,
                AIUsageRecordModel.created_at >= since_date
            )
        )
        res = (await db.execute(stmt)).first()

        return {
            "home_id": str(home_id),
            "quota": {
                "daily_requests_used": quota.current_daily_requests,
                "daily_requests_limit": quota.daily_request_limit,
                "daily_tokens_used": quota.current_daily_tokens,
                "daily_tokens_limit": quota.daily_token_limit,
                "monthly_cost_used_usd": float(quota.current_monthly_cost_usd),
                "monthly_cost_limit_usd": float(quota.monthly_cost_limit_usd)
            },
            "last_30_days": {
                "total_requests": res.total_requests if res else 0,
                "total_tokens": int(res.total_tokens) if res else 0,
                "total_cost_usd": float(res.total_cost) if res else 0.0,
                "avg_latency_ms": round(float(res.avg_latency_ms), 2) if res else 0.0
            }
        }
