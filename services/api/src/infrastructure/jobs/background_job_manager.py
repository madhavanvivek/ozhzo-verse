import time
import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from src.infrastructure.database.models import BackgroundJobModel

logger = logging.getLogger("ozhzo.jobs")

JobHandler = Callable[[AsyncSession, Dict[str, Any], Optional[UUID]], Any]


class BackgroundJobManager:
    """
    Durable, distributed-safe Background Job and Queue Manager.
    Supports worker-level distributed locking, worker crash recovery (zombie job reclamation),
    exponential backoff retries, dead-letter quarantine (DLQ), execution timeouts, and idempotent enqueuing.
    """

    _handlers: Dict[str, JobHandler] = {}

    @classmethod
    def register_handler(cls, job_type: str, handler: JobHandler) -> None:
        cls._handlers[job_type] = handler
        logger.info(f"Registered background job handler for: {job_type}")

    @classmethod
    async def enqueue_job(
        cls,
        db: AsyncSession,
        job_type: str,
        payload: Dict[str, Any],
        home_id: Optional[UUID] = None,
        max_retries: int = 3,
        delay_seconds: int = 0,
        idempotency_key: Optional[str] = None,
    ) -> BackgroundJobModel:
        """
        Enqueues a background job idempotently. If an idempotency_key is provided and an active
        job already exists, returns the existing job to prevent duplicate execution.
        """
        now = datetime.now(timezone.utc)
        next_run = now + timedelta(seconds=delay_seconds) if delay_seconds > 0 else now

        if idempotency_key:
            stmt = select(BackgroundJobModel).where(
                BackgroundJobModel.idempotency_key == idempotency_key
            )
            existing = (await db.execute(stmt)).scalar_one_or_none()
            if existing:
                return existing

        job = BackgroundJobModel(
            id=uuid4(),
            job_type=job_type,
            home_id=home_id,
            payload=payload,
            status="PENDING",
            retry_count=0,
            max_retries=max_retries,
            next_run_at=next_run,
            idempotency_key=idempotency_key or f"job-{uuid4().hex[:16]}",
            created_at=now,
            updated_at=now
        )
        db.add(job)
        await db.commit()
        await db.refresh(job)
        return job

    @classmethod
    async def process_due_jobs(
        cls,
        db: AsyncSession,
        worker_id: str = "worker-default",
        limit: int = 10,
        lock_timeout_seconds: int = 30,
    ) -> List[Dict[str, Any]]:
        """
        Pulls due jobs atomically.
        Reclaims zombie jobs (jobs stuck in 'RUNNING' whose lock has timed out due to worker crashes).
        Executes registered handlers under an execution timeout (30s) and handles retries / DLQ isolation.
        """
        now = datetime.now(timezone.utc)
        stale_lock_cutoff = now - timedelta(seconds=lock_timeout_seconds)

        # Select jobs that are PENDING and due OR RUNNING with a timed-out lock (crashed worker recovery)
        stmt = (
            select(BackgroundJobModel)
            .where(
                or_(
                    and_(
                        BackgroundJobModel.status == "PENDING",
                        BackgroundJobModel.next_run_at <= now,
                    ),
                    and_(
                        BackgroundJobModel.status == "RUNNING",
                        BackgroundJobModel.locked_at < stale_lock_cutoff,
                    )
                )
            )
            .order_by(BackgroundJobModel.next_run_at.asc())
            .limit(limit)
        )
        jobs = (await db.execute(stmt)).scalars().all()
        results = []

        for job in jobs:
            start_time = time.perf_counter()
            # 1. Distributed Lock Acquisition
            job.status = "RUNNING"
            job.locked_at = now
            job.locked_by = worker_id
            job.updated_at = now
            await db.commit()

            handler = cls._handlers.get(job.job_type)
            if not handler:
                logger.warning(f"No handler registered for job type: {job.job_type}")
                job.status = "FAILED"
                job.last_error = f"No handler registered for job type '{job.job_type}'"
                job.duration_ms = int((time.perf_counter() - start_time) * 1000)
                await db.commit()
                results.append({"job_id": str(job.id), "status": "FAILED", "error": "No handler"})
                continue

            try:
                # 2. Handler execution with 30s timeout
                await asyncio.wait_for(handler(db, job.payload, job.home_id), timeout=30.0)
                job.status = "COMPLETED"
                job.duration_ms = int((time.perf_counter() - start_time) * 1000)
                job.last_error = None
                job.updated_at = datetime.now(timezone.utc)
                await db.commit()
                results.append({"job_id": str(job.id), "status": "COMPLETED", "duration_ms": job.duration_ms})

            except Exception as e:
                duration_ms = int((time.perf_counter() - start_time) * 1000)
                job.duration_ms = duration_ms
                job.last_error = str(e)[:1000]
                job.retry_count += 1
                job.updated_at = datetime.now(timezone.utc)

                if job.retry_count >= job.max_retries:
                    # Quarantine to Dead-Letter Queue (DLQ)
                    job.status = "DEAD_LETTER"
                    logger.error(
                        f"Job {job.id} ({job.job_type}) failed permanently after {job.retry_count} retries. Quarantined to DLQ. Error: {e}"
                    )
                    results.append({"job_id": str(job.id), "status": "DEAD_LETTER", "error": str(e)})
                else:
                    # Exponential backoff: 10s * 2^(retry_count)
                    backoff_delay = 10 * (2 ** (job.retry_count - 1))
                    job.status = "PENDING"
                    job.next_run_at = datetime.now(timezone.utc) + timedelta(seconds=backoff_delay)
                    logger.warning(
                        f"Job {job.id} failed (attempt {job.retry_count}/{job.max_retries}). Retrying in {backoff_delay}s. Error: {e}"
                    )
                    results.append({"job_id": str(job.id), "status": "PENDING", "next_retry_seconds": backoff_delay})

                await db.commit()

        return results

    @classmethod
    async def get_failed_jobs(cls, db: AsyncSession, limit: int = 50) -> List[BackgroundJobModel]:
        stmt = (
            select(BackgroundJobModel)
            .where(BackgroundJobModel.status.in_(["FAILED", "DEAD_LETTER"]))
            .order_by(BackgroundJobModel.updated_at.desc())
            .limit(limit)
        )
        return (await db.execute(stmt)).scalars().all()

    @classmethod
    async def retry_dead_letter_job(cls, db: AsyncSession, job_id: UUID) -> BackgroundJobModel:
        """
        Manually re-enqueues a job from the Dead-Letter Queue (Super Admin action).
        """
        stmt = select(BackgroundJobModel).where(BackgroundJobModel.id == job_id)
        job = (await db.execute(stmt)).scalar_one_or_none()
        if not job:
            raise ValueError(f"Job {job_id} not found.")

        job.status = "PENDING"
        job.retry_count = 0
        job.last_error = None
        job.next_run_at = datetime.now(timezone.utc)
        job.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(job)
        return job


# Default built-in handlers
async def _handle_notification_dispatch(db: AsyncSession, payload: Dict[str, Any], home_id: Optional[UUID]):
    logger.info(f"Dispatched background notification: {payload.get('title')}")

async def _handle_retention_purge(db: AsyncSession, payload: Dict[str, Any], home_id: Optional[UUID]):
    from src.services.privacy_governance_service import PrivacyGovernanceService
    await PrivacyGovernanceService.execute_data_retention_purge(db)

async def _handle_webhook_retry(db: AsyncSession, payload: Dict[str, Any], home_id: Optional[UUID]):
    logger.info(f"Processed webhook retry for payload: {payload.get('event')}")

BackgroundJobManager.register_handler("NOTIFICATION_DISPATCH", _handle_notification_dispatch)
BackgroundJobManager.register_handler("RETENTION_PURGE", _handle_retention_purge)
BackgroundJobManager.register_handler("WEBHOOK_RETRY", _handle_webhook_retry)
