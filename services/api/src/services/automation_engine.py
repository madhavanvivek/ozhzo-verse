import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    AuditLogModel,
    AutomationExecutionModel,
    AutomationModel,
)
from src.schemas.automations import (
    ActionType,
    AutomationActionSchema,
    AutomationStatus,
    ConditionGroupSchema,
    ExecutionStatus,
    TriggerType,
)
from src.services.automation_action_engine import AutomationActionEngine
from src.services.automation_condition_engine import AutomationConditionEngine

logger = logging.getLogger("ozhzo.automation.engine")

MAX_EXECUTION_DEPTH = 3
FAILURE_THRESHOLD_FOR_ERROR = 5


class AutomationEngine:
    """
    Core Deterministic Automation Engine with Loop Protection, Idempotency, and Failure Health Tracking.
    """

    @staticmethod
    def generate_idempotency_key(
        automation_id: UUID, trigger_type: str, event_payload: Dict[str, Any]
    ) -> str:
        # Time-bucket scheduled triggers so legitimate recurring executions do not collide
        time_bucket = (
            event_payload.get("time_bucket")
            or event_payload.get("scheduled_at")
            or event_payload.get("execution_timestamp")
        )
        if not time_bucket and trigger_type in ("SCHEDULED_TIME", "SCHEDULED_CRON", "DAILY", "WEEKLY", "MONTHLY"):
            time_bucket = datetime.now(timezone.utc).strftime("%Y%m%d%H%M")

        entity_id = (
            event_payload.get("id")
            or event_payload.get("entity_id")
            or event_payload.get("item_id")
            or "event"
        )

        if time_bucket:
            raw = f"{automation_id}:{trigger_type}:{entity_id}:{time_bucket}"
        else:
            raw = f"{automation_id}:{trigger_type}:{entity_id}"

        return hashlib.sha256(raw.encode()).hexdigest()[:48]


    @classmethod
    async def execute_single_automation(
        cls,
        db: AsyncSession,
        automation: AutomationModel,
        event_payload: Dict[str, Any],
        user_role: str = "OWNER",
        user_id: Optional[UUID] = None,
        correlation_id: Optional[str] = None,
        depth: int = 0,
    ) -> AutomationExecutionModel:
        start_time = time.time()
        corr_id = correlation_id or str(uuid4())

        # 1. Loop Protection & Recursion Guard
        if depth >= MAX_EXECUTION_DEPTH:
            logger.warning(
                f"Loop protection triggered for automation {automation.id}. Depth {depth} >= {MAX_EXECUTION_DEPTH}."
            )
            exec_record = AutomationExecutionModel(
                id=uuid4(),
                automation_id=automation.id,
                home_id=automation.home_id,
                trigger_event=event_payload,
                evaluated_conditions={"error": "MAX_DEPTH_EXCEEDED"},
                actions_attempted=0,
                actions_succeeded=0,
                actions_failed=0,
                duration_ms=int((time.time() - start_time) * 1000),
                status=ExecutionStatus.SKIPPED.value,
                error_details="Loop protection triggered: Maximum automation execution depth reached.",
                correlation_id=corr_id,
                idempotency_key=f"loop-guard-{uuid4()}"
            )
            db.add(exec_record)
            await db.commit()
            return exec_record

        # 2. Idempotency Check
        idempotency_key = cls.generate_idempotency_key(
            automation.id, automation.trigger_type, event_payload
        )
        existing_stmt = select(AutomationExecutionModel).where(
            AutomationExecutionModel.idempotency_key == idempotency_key
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            logger.info(f"Duplicate execution suppressed by idempotency key {idempotency_key}")
            return existing

        # 3. Evaluate Conditions
        cond_dict = automation.conditions or {}
        try:
            cond_group = ConditionGroupSchema.model_validate(cond_dict) if cond_dict else None
        except Exception:
            cond_group = None

        conditions_met = AutomationConditionEngine.evaluate_group(cond_group, event_payload)

        if not conditions_met:
            exec_record = AutomationExecutionModel(
                id=uuid4(),
                automation_id=automation.id,
                home_id=automation.home_id,
                trigger_event=event_payload,
                evaluated_conditions={"conditions_met": False, "rules": cond_dict},
                actions_attempted=0,
                actions_succeeded=0,
                actions_failed=0,
                duration_ms=int((time.time() - start_time) * 1000),
                status=ExecutionStatus.SKIPPED.value,
                error_details="Conditions not satisfied.",
                correlation_id=corr_id,
                idempotency_key=idempotency_key
            )
            db.add(exec_record)
            await db.commit()
            return exec_record

        # 4. Execute Actions
        actions_raw = automation.actions or []
        actions_attempted = len(actions_raw)
        actions_succeeded = 0
        actions_failed = 0
        errors: List[str] = []

        for act_raw in actions_raw:
            try:
                action_schema = AutomationActionSchema.model_validate(act_raw)
                success, entity_id, err_msg = await AutomationActionEngine.execute_action(
                    db=db,
                    home_id=automation.home_id,
                    user_id=user_id or automation.created_by,
                    user_role=user_role,
                    action=action_schema,
                    context_payload=event_payload
                )
                if success:
                    actions_succeeded += 1
                else:
                    actions_failed += 1
                    errors.append(err_msg or "Unknown action failure")
            except Exception as ex:
                actions_failed += 1
                errors.append(str(ex))

        # 5. Determine Execution Status & Update Health
        if actions_failed == 0 and actions_succeeded > 0:
            exec_status = ExecutionStatus.SUCCESS
            automation.consecutive_failures = 0
        elif actions_succeeded > 0 and actions_failed > 0:
            exec_status = ExecutionStatus.PARTIAL
            automation.consecutive_failures += 1
            automation.failure_count += 1
        else:
            exec_status = ExecutionStatus.FAILED
            automation.consecutive_failures += 1
            automation.failure_count += 1

        # Check Failure Policy
        if automation.consecutive_failures >= FAILURE_THRESHOLD_FOR_ERROR:
            automation.status = AutomationStatus.ERROR.value
            logger.warning(
                f"Automation {automation.id} transitioned to ERROR status due to {automation.consecutive_failures} consecutive failures."
            )

        automation.last_run_at = datetime.now(timezone.utc)

        duration_ms = int((time.time() - start_time) * 1000)
        exec_record = AutomationExecutionModel(
            id=uuid4(),
            automation_id=automation.id,
            home_id=automation.home_id,
            trigger_event=event_payload,
            evaluated_conditions={"conditions_met": True, "rules": cond_dict},
            actions_attempted=actions_attempted,
            actions_succeeded=actions_succeeded,
            actions_failed=actions_failed,
            duration_ms=duration_ms,
            status=exec_status.value,
            error_details="; ".join(errors) if errors else None,
            correlation_id=corr_id,
            idempotency_key=idempotency_key
        )
        db.add(exec_record)

        # Audit Log
        audit = AuditLogModel(
            id=uuid4(),
            entity_type="AUTOMATION",
            entity_id=automation.id,
            action="AUTOMATION_EXECUTED",
            performed_by=user_id or automation.created_by,
            details=json.dumps({
                "execution_id": str(exec_record.id),
                "status": exec_status.value,
                "actions_succeeded": actions_succeeded,
                "actions_failed": actions_failed
            })
        )
        db.add(audit)
        await db.commit()

        return exec_record

    @classmethod
    async def dispatch_event(
        cls,
        db: AsyncSession,
        home_id: UUID,
        trigger_type: TriggerType,
        event_payload: Dict[str, Any],
        correlation_id: Optional[str] = None,
        depth: int = 0,
    ) -> List[AutomationExecutionModel]:
        """
        Dispatches a household event to all active enabled automations in the Home.
        """
        stmt = (
            select(AutomationModel)
            .where(
                AutomationModel.home_id == home_id,
                AutomationModel.trigger_type == trigger_type.value,
                AutomationModel.enabled.is_(True),
                AutomationModel.status == AutomationStatus.ACTIVE.value,
                AutomationModel.deleted_at.is_(None)
            )
        )
        automations = (await db.execute(stmt)).scalars().all()
        results: List[AutomationExecutionModel] = []

        for auto in automations:
            res = await cls.execute_single_automation(
                db=db,
                automation=auto,
                event_payload=event_payload,
                user_role="OWNER",
                correlation_id=correlation_id,
                depth=depth
            )
            results.append(res)

        return results


# Global automation engine singleton
automation_engine = AutomationEngine()
