from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import logging
import time
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import HomeContext
from src.core.ai_config import AIModelConfig, get_ai_config
from src.core.security_ai import enforce_prompt_guardrails
from src.domain.permissions import has_permission
from src.infrastructure.database.models import (
    AuditLogModel,
    BillModel,
    EventModel,
    InventoryItemModel,
    PurchaseItemModel,
    StockMovementModel,
    TaskModel
)
from src.schemas.ai import (
    AIActionConfirmRequest,
    AIActionExecutionResult,
    AIActionProposalDTO,
    AIActionType,
    AIChatRequest,
    AIChatResponse,
    AIIntentType,
    AIRecommendationDTO,
    AIUsageMetricsDTO,
)
from src.services.ai_context_builder import HouseholdContextBuilder
from src.services.ai_cost_controller import AICostController
from src.services.ai_provider import BaseAIProvider, get_ai_provider

logger = logging.getLogger("ozhzo.ai.assistant")


class AIAssistantService:
    """
    Central orchestration service for Household AI Intelligence.
    Adheres strictly to the principle: AI proposes -> User confirms -> Authoritative Domain Service executes.
    """

    def __init__(self, provider: Optional[BaseAIProvider] = None):
        self.config = get_ai_config()
        self.provider = provider or get_ai_provider(self.config)
        # In-memory proposal cache: {action_id: (home_id, user_id, proposal_dto, expires_at)}
        self._staged_proposals: Dict[str, Dict[str, Any]] = {}
        # Usage metrics per home: {home_id: {"interactions": int, "actions_proposed": int, "actions_executed": int}}
        self._usage_metrics: Dict[str, Dict[str, int]] = {}

    def _track_interaction(self, home_id: str, is_proposal: bool = False, is_execution: bool = False):
        if home_id not in self._usage_metrics:
            self._usage_metrics[home_id] = {
                "interactions": 0,
                "actions_proposed": 0,
                "actions_executed": 0
            }
        self._usage_metrics[home_id]["interactions"] += 1
        if is_proposal:
            self._usage_metrics[home_id]["actions_proposed"] += 1
        if is_execution:
            self._usage_metrics[home_id]["actions_executed"] += 1

    async def process_chat(
        self, db: AsyncSession, home_ctx: HomeContext, request: AIChatRequest
    ) -> AIChatResponse:
        home_id_str = str(home_ctx.home_id)
        self._track_interaction(home_id_str)
        start_time = time.perf_counter()

        sanitized_message = enforce_prompt_guardrails(request.message)

        # 1. Build role-filtered minimum context
        context = await HouseholdContextBuilder.build_context(db, home_ctx)

        # 2. Quota check
        try:
            await AICostController.check_quota_before_request(db, home_ctx.home_id)
        except HTTPException:
            raise
        except Exception:
            pass

        # 3. Detect Intent and extract parameters
        intent, confidence, params = await self.provider.detect_intent(sanitized_message, context)


        action_proposal: Optional[AIActionProposalDTO] = None

        # 3. Handle Write Actions with Permission Checks & Action Proposal Staging
        if intent == AIIntentType.CREATE_TASK:
            if not has_permission(home_ctx.role, "tasks:create"):
                return AIChatResponse(
                    message=f"I cannot create a task because your role ({home_ctx.role}) does not have permission to add household tasks.",
                    detected_intent=intent,
                    intent_confidence=confidence,
                    suggested_quick_replies=["Show active tasks", "Check pantry stock"]
                )

            task_params = params or {"title": "New Task", "priority": "NORMAL", "due_date": date.today().isoformat()}
            action_proposal = AIActionProposalDTO(
                action_type=AIActionType.CREATE_TASK,
                title=f"Create Task: {task_params.get('title', 'Chore')}",
                description=f"Create task '{task_params.get('title')}' with {task_params.get('priority', 'NORMAL')} priority due {task_params.get('due_date', 'today')}.",
                params=task_params,
                expires_at=datetime.utcnow() + timedelta(minutes=15)
            )

        elif intent == AIIntentType.ADD_SHOPPING_ITEM:
            if not has_permission(home_ctx.role, "shopping:create"):
                return AIChatResponse(
                    message=f"Your role ({home_ctx.role}) does not have permission to add items to the shopping list.",
                    detected_intent=intent,
                    intent_confidence=confidence,
                    suggested_quick_replies=["Show shopping list", "Check low stock"]
                )

            shop_params = params or {"item_name": "Grocery Item", "quantity": 1.0, "unit": "item"}
            action_proposal = AIActionProposalDTO(
                action_type=AIActionType.ADD_SHOPPING_ITEM,
                title=f"Add to Shopping List: {shop_params.get('item_name')}",
                description=f"Add {shop_params.get('quantity', 1)} {shop_params.get('unit', 'item')} of {shop_params.get('item_name')} to the household purchase list.",
                params=shop_params,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
            )

        elif intent == AIIntentType.CREATE_BILL:
            if not has_permission(home_ctx.role, "bills:create"):
                return AIChatResponse(
                    message=f"Your role ({home_ctx.role}) cannot create bills. Only Home Owners and Admins can record financial expenses.",
                    detected_intent=intent,
                    intent_confidence=confidence,
                    suggested_quick_replies=["Show active tasks", "Check shopping list"]
                )

            bill_params = params or {"title": "Utility Expense", "amount": 1000.0, "currency": context.get("currency", "INR"), "due_date": (date.today() + timedelta(days=7)).isoformat()}
            action_proposal = AIActionProposalDTO(
                action_type=AIActionType.CREATE_BILL,
                title=f"Record Bill: {bill_params.get('title')}",
                description=f"Record bill '{bill_params.get('title')}' of {bill_params.get('currency', 'INR')} {float(bill_params.get('amount', 0)):,.2f} due on {bill_params.get('due_date')}.",
                params=bill_params,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=15)
            )

        elif intent == AIIntentType.CREATE_EVENT:
            if not has_permission(home_ctx.role, "calendar:create"):
                return AIChatResponse(
                    message=f"Your role ({home_ctx.role}) cannot add calendar events.",
                    detected_intent=intent,
                    intent_confidence=confidence,
                    suggested_quick_replies=["Show active tasks", "Check shopping list"]
                )


            evt_params = params or {"title": "Family Event", "start_time": datetime.utcnow().isoformat()}
            action_proposal = AIActionProposalDTO(
                action_type=AIActionType.CREATE_EVENT,
                title=f"Schedule Event: {evt_params.get('title')}",
                description=f"Add event '{evt_params.get('title')}' to household calendar.",
                params=evt_params,
                expires_at=datetime.utcnow() + timedelta(minutes=15)
            )

        # Stage proposal in cache if created
        if action_proposal:
            self._staged_proposals[action_proposal.id] = {
                "home_id": home_id_str,
                "user_id": str(home_ctx.user.id),
                "proposal": action_proposal,
                "expires_at": datetime.now(timezone.utc) + timedelta(minutes=15)
            }
            self._track_interaction(home_id_str, is_proposal=True)

        # 4. Generate Natural Language Response
        reply_text, quick_replies = await self.provider.generate_response(
            request.message, intent, context, action_proposal
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)
        try:
            await AICostController.record_usage(
                db=db,
                home_id=home_ctx.home_id,
                user_id=home_ctx.user.id,
                prompt_tokens=max(len(request.message) // 4, 10),
                completion_tokens=max(len(reply_text) // 4, 20),
                latency_ms=latency_ms,
                provider="mock",
                model_name="ozhzo-neural-v1",
                status_str="SUCCESS"
            )
        except Exception as e:
            logger.warning(f"AI usage recording notice: {e}")

        return AIChatResponse(
            message=reply_text,
            detected_intent=intent,
            intent_confidence=confidence,
            action_proposal=action_proposal,
            data_payload=context if intent in (AIIntentType.QUERY_TASKS, AIIntentType.QUERY_BILLS, AIIntentType.QUERY_INVENTORY, AIIntentType.QUERY_SHOPPING) else None,
            suggested_quick_replies=quick_replies
        )


    async def execute_action_proposal(
        self, db: AsyncSession, home_ctx: HomeContext, action_id: str
    ) -> AIActionExecutionResult:
        staged = self._staged_proposals.get(action_id)
        if not staged:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Action proposal not found or has expired. Please request the action again."
            )

        home_id_str = str(home_ctx.home_id)
        if staged["home_id"] != home_id_str:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot execute an action proposal belonging to a different home context."
            )

        if datetime.now(timezone.utc) > staged["expires_at"]:
            del self._staged_proposals[action_id]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Action proposal has expired. Please request the action again."
            )

        proposal: AIActionProposalDTO = staged["proposal"]
        executed_entity_id: Optional[str] = None
        message = ""

        # Execute through Authoritative Domain Models & Invariants
        if proposal.action_type == AIActionType.CREATE_TASK:
            due_str = proposal.params.get("due_date")
            due_val = date.fromisoformat(due_str) if due_str else None
            new_task = TaskModel(
                id=uuid4(),
                home_id=home_ctx.home_id,
                title=proposal.params.get("title", "New Task"),
                priority=proposal.params.get("priority", "NORMAL"),
                status="TODO",
                due_date=due_val,
                created_by=home_ctx.user.id,
                version=1
            )
            db.add(new_task)
            executed_entity_id = str(new_task.id)
            message = f"Task '{new_task.title}' was successfully created in your household."

        elif proposal.action_type == AIActionType.ADD_SHOPPING_ITEM:
            new_item = PurchaseItemModel(
                id=uuid4(),
                home_id=home_ctx.home_id,
                name=proposal.params.get("item_name", "Item"),
                quantity=Decimal(str(proposal.params.get("quantity", 1.0))),
                unit=proposal.params.get("unit", "item"),
                status="PENDING",
                added_by=home_ctx.user.id
            )
            db.add(new_item)
            executed_entity_id = str(new_item.id)
            message = f"Added '{new_item.name}' ({new_item.quantity} {new_item.unit}) to your shopping list."


        elif proposal.action_type == AIActionType.CREATE_BILL:
            due_str = proposal.params.get("due_date")
            due_val = date.fromisoformat(due_str) if due_str else date.today()
            new_bill = BillModel(
                id=uuid4(),
                home_id=home_ctx.home_id,
                title=proposal.params.get("title", "Bill"),
                expected_amount=Decimal(str(proposal.params.get("amount", 0.0))),
                currency=proposal.params.get("currency", "INR"),
                due_date=due_val,
                status="UNPAID",
                created_by=home_ctx.user.id,
                version=1
            )
            db.add(new_bill)
            executed_entity_id = str(new_bill.id)
            message = f"Bill '{new_bill.title}' for {new_bill.currency} {new_bill.expected_amount:.2f} recorded."

        elif proposal.action_type == AIActionType.CREATE_EVENT:
            start_val = datetime.fromisoformat(proposal.params.get("start_time", datetime.now(timezone.utc).isoformat()))
            new_evt = EventModel(
                id=uuid4(),
                home_id=home_ctx.home_id,
                title=proposal.params.get("title", "Event"),
                start_time=start_val,
                end_time=start_val + timedelta(hours=1),
                status="CONFIRMED",
                created_by=home_ctx.user.id
            )
            db.add(new_evt)
            executed_entity_id = str(new_evt.id)
            message = f"Event '{new_evt.title}' scheduled for {new_evt.start_time.strftime('%d %b %H:%M')}."

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unsupported action type '{proposal.action_type}'"
            )

        # Record Audit Log
        import json
        audit = AuditLogModel(
            id=uuid4(),
            entity_type=proposal.action_type.value,
            entity_id=UUID(executed_entity_id) if executed_entity_id else uuid4(),
            action="AI_ACTION_EXECUTED",
            performed_by=home_ctx.user.id,
            details=json.dumps({
                "action_id": action_id,
                "action_type": proposal.action_type.value,
                "params": proposal.params
            })
        )
        db.add(audit)
        await db.commit()

        # Clean up staged cache
        del self._staged_proposals[action_id]
        self._track_interaction(home_id_str, is_execution=True)

        return AIActionExecutionResult(
            success=True,
            action_id=action_id,
            action_type=proposal.action_type,
            executed_entity_id=executed_entity_id,
            message=message,
            audit_log_id=str(audit.id)
        )

    async def get_recommendations(
        self, db: AsyncSession, home_ctx: HomeContext
    ) -> List[AIRecommendationDTO]:
        context = await HouseholdContextBuilder.build_context(db, home_ctx)
        recs = await self.provider.generate_recommendations(context)
        # Stage any action proposals present in recommendations
        for r in recs:
            if r.suggested_action:
                self._staged_proposals[r.suggested_action.id] = {
                    "home_id": str(home_ctx.home_id),
                    "user_id": str(home_ctx.user.id),
                    "proposal": r.suggested_action,
                    "expires_at": datetime.now(timezone.utc) + timedelta(minutes=30)
                }
        return recs


    def get_usage(self, home_id: UUID) -> AIUsageMetricsDTO:
        home_id_str = str(home_id)
        m = self._usage_metrics.get(home_id_str, {"interactions": 0, "actions_proposed": 0, "actions_executed": 0})
        interactions = m["interactions"]
        return AIUsageMetricsDTO(
            home_id=home_id_str,
            total_interactions=interactions,
            total_actions_proposed=m["actions_proposed"],
            total_actions_executed=m["actions_executed"],
            total_input_tokens=interactions * 120,
            total_output_tokens=interactions * 80,
            estimated_cost_usd=round((interactions * 120 * 0.00015 + interactions * 80 * 0.0006) / 1000, 5)
        )


# Global singleton instance
ai_assistant_service = AIAssistantService()
