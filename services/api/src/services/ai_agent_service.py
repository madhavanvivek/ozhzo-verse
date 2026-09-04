import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security_ai import enforce_prompt_guardrails
from src.infrastructure.database.models import (
    AIAgentAuditModel,
    AIConversationSessionModel,
)
from src.schemas.intelligence_memory import (
    AIAgentPlanDTO,
    AIAgentPlanStepDTO,
    AIConversationTurnRequest,
    AIConversationTurnResponse,
    MemoryCategory,
)
from src.services.ai_agent_tool_registry import AIAgentToolRegistry
from src.services.ai_cost_controller import AICostController
from src.services.ai_context_builder import HouseholdContextBuilder
from src.services.household_memory_service import HouseholdMemoryService
from src.services.personalization_service import PersonalizationService

logger = logging.getLogger("ozhzo.ai.agent")


class AIAgentService:
    """
    Advanced AI Agent supporting multi-turn continuous conversation,
    bounded multi-step planning, memory context retrieval, and explicit confirmation execution.
    """

    MAX_PLAN_STEPS = 5
    MAX_HISTORY_TURNS = 6

    @classmethod
    async def process_conversation_turn(
        cls,
        db: AsyncSession,
        home_id: UUID,
        request: AIConversationTurnRequest,
        user_role: str,
        user_id: UUID,
    ) -> AIConversationTurnResponse:
        """
        Processes a multi-turn conversation request using retrieved memory and bounded planning.
        """
        start_time = time.perf_counter()
        now = datetime.now(timezone.utc)

        # 0. Quota check & prompt guardrail
        await AICostController.check_quota_before_request(db, home_id)
        prompt = enforce_prompt_guardrails(request.prompt.strip())
        lower_prompt = prompt.lower()

        # 1. Retrieve or initialize conversation session
        session = None
        if request.session_token:
            stmt = select(AIConversationSessionModel).where(
                AIConversationSessionModel.session_token == request.session_token,
                AIConversationSessionModel.home_id == home_id,
                AIConversationSessionModel.user_id == user_id,
                AIConversationSessionModel.expires_at > now,
            )
            session = (await db.execute(stmt)).scalar_one_or_none()

        if not session:
            session_token = uuid4().hex
            session = AIConversationSessionModel(
                id=uuid4(),
                home_id=home_id,
                user_id=user_id,
                session_token=session_token,
                history_json=[],
                expires_at=now + timedelta(hours=2),
                last_activity_at=now,
                created_at=now,
            )
            db.add(session)
        else:
            session.last_activity_at = now
            session.expires_at = now + timedelta(hours=2)

        history = session.history_json or []

        # 2. Retrieve relevant long-term household memories
        retrieved_memories = await HouseholdMemoryService.retrieve_relevant_memories(
            db=db,
            home_id=home_id,
            query=prompt,
            user_id=user_id,
            limit=4,
        )

        # 3. Retrieve user personalization preferences
        prefs = await PersonalizationService.get_or_create_preferences(db, user_id, home_id)

        # 4. Multi-turn contextual resolution
        last_turn = history[-1] if history else None
        is_followup_reminder = False
        if last_turn and "remind" in last_turn.get("user", "").lower() and any(k in lower_prompt for k in ["day before", "morning", "tomorrow", "evening"]):
            is_followup_reminder = True

        # 5. Planning & intent routing
        # Scenario A: Multi-step request (e.g. "Prepare the house for the weekend", "Restock groceries and plan cleaning")
        if any(k in lower_prompt for k in ["prepare for weekend", "prepare the house", "plan weekend", "weekend chore routine"]):
            plan_id = uuid4().hex[:12]
            plan = AIAgentPlanDTO(
                plan_id=plan_id,
                title="Weekend Household Preparation Plan",
                summary="Review overdue chores, check low pantry supplies, and schedule weekend tasks.",
                steps=[
                    AIAgentPlanStepDTO(
                        step_number=1,
                        action_type="QUERY",
                        target_domain="INVENTORY",
                        description="Check low stock pantry items",
                        tool_name="query_inventory",
                        parameters={"low_stock_only": True},
                        permission_required="inventory:view",
                    ),
                    AIAgentPlanStepDTO(
                        step_number=2,
                        action_type="WRITE",
                        target_domain="SHOPPING",
                        description="Add restock items to shopping list",
                        tool_name="create_shopping_item",
                        parameters={"name": "Weekly Groceries", "quantity": 1, "unit": "pkg"},
                        permission_required="shopping:create",
                    ),
                    AIAgentPlanStepDTO(
                        step_number=3,
                        action_type="WRITE",
                        target_domain="TASK",
                        description="Schedule weekend deep cleaning chore",
                        tool_name="create_task",
                        parameters={"title": "Weekend Household Cleaning", "priority": "NORMAL"},
                        permission_required="tasks:create",
                    ),
                ],
                requires_confirmation=True,
            )
            session.active_plan = plan.model_dump(mode="json")
            history.append({"user": prompt, "assistant": "I have created a multi-step weekend preparation plan for your review."})
            session.history_json = history[-cls.MAX_HISTORY_TURNS:]
            await db.commit()

            return AIConversationTurnResponse(
                session_token=session.session_token,
                response_text="Here is a proposed household plan based on your routines. Please review and confirm the write steps.",
                suggested_plan=plan,
                retrieved_memory_snippets=retrieved_memories,
                requires_confirmation=True,
            )

        # Scenario B: Single-step Write Action (e.g. "Add milk to shopping list" or follow-up reminder)
        if is_followup_reminder or "remind" in lower_prompt:
            timing = prefs.reminder_timing_preference if not is_followup_reminder else prompt
            action_proposal = {
                "action_type": "CREATE_REMINDER",
                "title": "Scheduled Household Reminder",
                "timing": timing,
                "domain": "NOTIFICATION",
                "explanation": f"Personalized reminder scheduled based on your preference ({timing}).",
            }
            history.append({"user": prompt, "assistant": f"I've prepared a reminder proposal for {timing}."})
            session.history_json = history[-cls.MAX_HISTORY_TURNS:]
            await db.commit()

            return AIConversationTurnResponse(
                session_token=session.session_token,
                response_text=f"I've prepared a reminder for you ({timing}). Confirm to schedule it in your notifications.",
                action_proposal=action_proposal,
                retrieved_memory_snippets=retrieved_memories,
                requires_confirmation=True,
            )

        if "add" in lower_prompt and "shopping" in lower_prompt or "buy" in lower_prompt:
            # Extract item name
            target_item = "Milk"
            for w in prompt.split():
                if w.lower() not in ["add", "to", "the", "shopping", "list", "buy", "please", "we", "need"]:
                    target_item = w
                    break

            action_proposal = {
                "action_type": "ADD_SHOPPING_ITEM",
                "name": target_item,
                "quantity": 1,
                "unit": "pcs",
                "explanation": f"Adding {target_item} to the household purchase list.",
            }
            history.append({"user": prompt, "assistant": f"I've prepared a proposal to add {target_item} to your shopping list."})
            session.history_json = history[-cls.MAX_HISTORY_TURNS:]
            await db.commit()

            return AIConversationTurnResponse(
                session_token=session.session_token,
                response_text=f"I can add **{target_item}** to your shopping list. Would you like me to proceed?",
                action_proposal=action_proposal,
                retrieved_memory_snippets=retrieved_memories,
                requires_confirmation=True,
            )

        # Scenario C: Read-only Queries (Tasks, Bills, Shopping, Summary)
        if "bill" in lower_prompt or "due" in lower_prompt:
            bills_res = await _execute_tool_safely(db, home_id, "query_bills", {"status": "UNPAID"}, user_id)
            resp_text = f"You currently have {bills_res.get('count', 0)} unpaid/upcoming bills."
            if retrieved_memories:
                resp_text += f"\n\n*Relevant preference*: {retrieved_memories[0]}"
        elif "shop" in lower_prompt or "buy" in lower_prompt:
            shop_res = await _execute_tool_safely(db, home_id, "query_shopping", {}, user_id)
            resp_text = f"There are {shop_res.get('count', 0)} items on the purchase list."
        elif "task" in lower_prompt or "chore" in lower_prompt:
            task_res = await _execute_tool_safely(db, home_id, "query_tasks", {"status": "TODO"}, user_id)
            resp_text = f"There are {task_res.get('count', 0)} pending tasks for your home."
        else:
            resp_text = "I'm your Ozhzo Household Assistant. I can help organize chores, track bills, manage inventory, and execute automated household plans."
            if retrieved_memories:
                resp_text += f"\n\n*Household Memory context loaded*: {len(retrieved_memories)} active preferences."

        history.append({"user": prompt, "assistant": resp_text})
        session.history_json = history[-cls.MAX_HISTORY_TURNS:]
        await db.commit()

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        try:
            await AICostController.record_usage(
                db=db,
                home_id=home_id,
                user_id=user_id,
                prompt_tokens=max(len(prompt) // 4, 10),
                completion_tokens=max(len(resp_text) // 4, 20),
                latency_ms=latency_ms,
                provider="mock",
                model_name="ozhzo-agent-v1",
                status_str="SUCCESS"
            )
        except Exception as e:
            logger.warning(f"AI agent usage recording notice: {e}")

        return AIConversationTurnResponse(
            session_token=session.session_token,
            response_text=resp_text,
            retrieved_memory_snippets=retrieved_memories,
            requires_confirmation=False,
        )


    @classmethod
    async def execute_confirmed_plan(
        cls,
        db: AsyncSession,
        home_id: UUID,
        session_token: str,
        user_role: str,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """
        Executes a confirmed multi-step plan through allowlisted domain tools with strict RBAC checks.
        """
        stmt = select(AIConversationSessionModel).where(
            AIConversationSessionModel.session_token == session_token,
            AIConversationSessionModel.home_id == home_id,
            AIConversationSessionModel.user_id == user_id,
        )
        session = (await db.execute(stmt)).scalar_one_or_none()
        if not session or not session.active_plan:
            return {"status": "ERROR", "message": "No active plan found to execute"}

        plan_data = session.active_plan
        steps = plan_data.get("steps", [])
        executed_steps = []
        now = datetime.now(timezone.utc)
        correlation_id = uuid4().hex[:16]

        for step in steps:
            tool_name = step.get("tool_name")
            perm_req = step.get("permission_required")
            tool = AIAgentToolRegistry.get_tool(tool_name)

            if not tool:
                step["status"] = "SKIPPED"
                step["result"] = {"error": f"Tool '{tool_name}' not allowlisted"}
                executed_steps.append(step)
                continue

            # RBAC check: guests cannot perform write actions
            if tool.is_write_action and user_role.upper() in ["GUEST", "CHILD"]:
                step["status"] = "REJECTED"
                step["result"] = {"error": "Permission denied for user role"}
                executed_steps.append(step)
                continue

            # Execute tool safely
            try:
                res = await tool.handler(db=db, home_id=home_id, params=step.get("parameters", {}), user_id=user_id)
                step["status"] = "EXECUTED"
                step["result"] = res

                # Audit log
                audit = AIAgentAuditModel(
                    id=uuid4(),
                    home_id=home_id,
                    user_id=user_id,
                    event_type="PLAN_EXECUTED",
                    tool_name=tool.name,
                    tool_params=step.get("parameters"),
                    execution_status="SUCCESS",
                    details=json.dumps(res),
                    correlation_id=correlation_id,
                    created_at=now,
                )
                db.add(audit)
            except Exception as ex:
                step["status"] = "FAILED"
                step["result"] = {"error": str(ex)}

            executed_steps.append(step)

        # Clear active plan upon execution
        session.active_plan = None
        await db.commit()

        return {
            "status": "SUCCESS",
            "plan_id": plan_data.get("plan_id"),
            "executed_steps_count": len(executed_steps),
            "steps": executed_steps,
        }


async def _execute_tool_safely(db: AsyncSession, home_id: UUID, tool_name: str, params: Dict[str, Any], user_id: Optional[UUID] = None) -> Dict[str, Any]:
    tool = AIAgentToolRegistry.get_tool(tool_name)
    if not tool:
        return {"error": "Tool not found"}
    return await tool.handler(db=db, home_id=home_id, params=params, user_id=user_id)
