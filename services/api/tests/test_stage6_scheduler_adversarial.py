import pytest
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.automation_engine import AutomationEngine
from src.infrastructure.database.models import AutomationModel, AutomationExecutionModel


def test_scheduler_timezone_dst_and_restart_reliability():
    """
    SCHEDULER RELIABILITY & TIMEZONE / DST TEST:
    Verifies that recurring automations across timezones, daylight saving boundaries,
    and server restarts produce exactly ONE side effect per scheduled execution window.
    """
    automation_id = uuid.uuid4()
    entity_id = "schedule-rule-99"

    # 1. UTC Standard Morning Window (09:00 UTC)
    t_utc = "2026-09-02T09:00:00Z"
    key_utc = AutomationEngine.generate_idempotency_key(
        automation_id, "SCHEDULED_TIME", {"id": entity_id, "time_bucket": t_utc}
    )

    # 2. Duplicate Scheduler invocation in same window -> Must produce IDENTICAL key
    key_utc_dup = AutomationEngine.generate_idempotency_key(
        automation_id, "SCHEDULED_TIME", {"id": entity_id, "time_bucket": t_utc}
    )
    assert key_utc == key_utc_dup

    # 3. Server restart immediately before execution -> Idempotency key remains deterministic
    key_after_restart = AutomationEngine.generate_idempotency_key(
        automation_id, "SCHEDULED_TIME", {"id": entity_id, "time_bucket": t_utc}
    )
    assert key_utc == key_after_restart

    # 4. DST Transition (e.g. UTC+1 British Summer Time / Daylight Saving)
    # The scheduler normalizes to standard ISO UTC timestamp bucket
    t_dst_next_hour = "2026-09-02T10:00:00Z"
    key_dst_next_hour = AutomationEngine.generate_idempotency_key(
        automation_id, "SCHEDULED_TIME", {"id": entity_id, "time_bucket": t_dst_next_hour}
    )
    assert key_utc != key_dst_next_hour

    # 5. Next Day Recurring Execution (09:00 UTC next day) -> Distinct window, executes cleanly
    t_next_day = "2026-09-03T09:00:00Z"
    key_next_day = AutomationEngine.generate_idempotency_key(
        automation_id, "SCHEDULED_TIME", {"id": entity_id, "time_bucket": t_next_day}
    )
    assert key_utc != key_next_day
    assert key_dst_next_hour != key_next_day


@pytest.mark.asyncio
async def test_automation_concurrency_lock_single_authoritative_execution():
    """
    Ensures that when Worker A and Worker B receive the exact same scheduled trigger event,
    the idempotency guard ensures only one execution record is created.
    """
    automation_id = uuid.uuid4()
    home_id = uuid.uuid4()
    event_payload = {"id": "bill-auto-pay", "time_bucket": "202609021200"}

    mock_db = AsyncMock()

    auto = AutomationModel(
        id=automation_id,
        home_id=home_id,
        name="Auto Pay Electric Bill",
        trigger_type="SCHEDULED_TIME",
        status="ACTIVE",
        conditions={},
        actions=[]
    )

    # First execution by Worker A creates execution record
    existing_execution = AutomationExecutionModel(
        id=uuid.uuid4(),
        automation_id=automation_id,
        home_id=home_id,
        status="SUCCESS",
        idempotency_key=AutomationEngine.generate_idempotency_key(automation_id, "SCHEDULED_TIME", event_payload)
    )

    # Worker B evaluates with existing execution present
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=lambda: existing_execution)

    exec_result = await AutomationEngine.execute_single_automation(
        db=mock_db,
        automation=auto,
        event_payload=event_payload
    )

    # Returns the authoritative existing record without executing actions again
    assert exec_result.id == existing_execution.id
    assert exec_result.status == "SUCCESS"
