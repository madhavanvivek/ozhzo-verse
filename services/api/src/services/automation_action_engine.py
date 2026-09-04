from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
import logging
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.permissions import has_permission
from src.infrastructure.database.models import (
    AuditLogModel,
    BillModel,
    EventModel,
    HouseholdRecommendationModel,
    InventoryItemModel,
    NotificationModel,
    PurchaseItemModel,
    StockMovementModel,
    TaskModel,
)
from src.schemas.automations import ActionType, AutomationActionSchema

logger = logging.getLogger("ozhzo.automation.actions")


class AutomationActionEngine:
    """
    Executes automation actions strictly through authoritative domain models and business invariants.
    """

    @classmethod
    async def execute_action(
        cls,
        db: AsyncSession,
        home_id: UUID,
        user_id: Optional[UUID],
        user_role: str,
        action: AutomationActionSchema,
        context_payload: Dict[str, Any],
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Returns: (success: bool, entity_id: Optional[str], error_message: Optional[str])
        """
        action_type = action.action_type
        params = action.params or {}

        try:
            # 1. CREATE_TASK
            if action_type == ActionType.CREATE_TASK:
                if not has_permission(user_role, "tasks:create"):
                    return False, None, f"User role {user_role} unauthorized for tasks:create"

                title = params.get("title") or context_payload.get("title") or "Automated Household Task"
                priority = params.get("priority", "NORMAL")
                due_days = params.get("due_in_days", 1)
                due_val = date.today() + timedelta(days=due_days)

                new_task = TaskModel(
                    id=uuid4(),
                    home_id=home_id,
                    title=title,
                    priority=priority,
                    status="TODO",
                    due_date=due_val,
                    assigned_to=UUID(params["assigned_to"]) if params.get("assigned_to") else None,
                    created_by=user_id,
                    version=1
                )
                db.add(new_task)
                return True, str(new_task.id), None

            # 2. ADD_SHOPPING_ITEM
            elif action_type == ActionType.ADD_SHOPPING_ITEM:
                if not has_permission(user_role, "shopping:create"):
                    return False, None, f"User role {user_role} unauthorized for shopping:create"

                item_name = params.get("name") or context_payload.get("name") or "Household Item"
                quantity = Decimal(str(params.get("quantity", 1.0)))
                unit = params.get("unit") or context_payload.get("unit") or "pcs"
                inv_id_raw = params.get("inventory_item_id") or context_payload.get("id")
                inv_item_id = UUID(str(inv_id_raw)) if inv_id_raw else None

                new_item = PurchaseItemModel(
                    id=uuid4(),
                    home_id=home_id,
                    inventory_item_id=inv_item_id,
                    name=item_name,
                    quantity=quantity,
                    unit=unit,
                    status="PENDING",
                    added_by=user_id
                )
                db.add(new_item)
                return True, str(new_item.id), None

            # 3. RESTOCK_INVENTORY
            elif action_type == ActionType.RESTOCK_INVENTORY:
                if not has_permission(user_role, "inventory:edit"):
                    return False, None, f"User role {user_role} unauthorized for inventory:edit"

                inv_id_raw = params.get("inventory_item_id") or context_payload.get("id")
                if not inv_id_raw:
                    return False, None, "Missing inventory_item_id for RESTOCK_INVENTORY"

                inv_id = UUID(str(inv_id_raw))
                item_stmt = select(InventoryItemModel).where(
                    InventoryItemModel.id == inv_id,
                    InventoryItemModel.home_id == home_id,
                    InventoryItemModel.deleted_at.is_(None)
                )
                item = (await db.execute(item_stmt)).scalar_one_or_none()
                if not item:
                    return False, None, f"Inventory item {inv_id} not found"

                restock_qty = Decimal(str(params.get("quantity", 1.0)))
                prev_qty = item.quantity
                new_qty = prev_qty + restock_qty
                item.quantity = new_qty
                if new_qty > item.min_threshold:
                    item.status = "IN_STOCK"

                movement = StockMovementModel(
                    id=uuid4(),
                    home_id=home_id,
                    inventory_item_id=item.id,
                    movement_type="IN",
                    quantity=restock_qty,
                    previous_quantity=prev_qty,
                    new_quantity=new_qty,
                    reason="AUTOMATION_RESTOCK",
                    performed_by=user_id
                )
                db.add(movement)
                return True, str(item.id), None

            # 4. CREATE_NOTIFICATION
            elif action_type == ActionType.CREATE_NOTIFICATION:
                title = params.get("title") or "Automation Alert"
                body = params.get("body") or f"Triggered action for {home_id}"
                priority = params.get("priority", "NORMAL")
                category = params.get("category", "AUTOMATION")

                notification = NotificationModel(
                    id=uuid4(),
                    home_id=home_id,
                    user_id=user_id,
                    title=title,
                    body=body,
                    category=category,
                    priority=priority,
                    requires_action=bool(params.get("requires_action", False)),
                    dedup_key=params.get("dedup_key")
                )
                db.add(notification)
                return True, str(notification.id), None

            # 5. CREATE_EVENT
            elif action_type == ActionType.CREATE_EVENT:
                if not has_permission(user_role, "calendar:create"):
                    return False, None, f"User role {user_role} unauthorized for calendar:create"

                evt_title = params.get("title") or "Automated Household Schedule"
                start_dt = datetime.now(timezone.utc) + timedelta(days=params.get("days_ahead", 1))
                new_event = EventModel(
                    id=uuid4(),
                    home_id=home_id,
                    title=evt_title,
                    start_time=start_dt,
                    end_time=start_dt + timedelta(hours=1),
                    status="CONFIRMED",
                    created_by=user_id
                )
                db.add(new_event)
                return True, str(new_event.id), None

            # 6. CREATE_RECOMMENDATION
            elif action_type == ActionType.CREATE_RECOMMENDATION:
                import hashlib
                rec_title = params.get("title", "Household Recommendation")
                rec_reason = params.get("reason", "Proactive suggestion")
                domain = params.get("domain", "AUTOMATION")
                dedup_hash = hashlib.sha256(f"{home_id}:{domain}:{rec_title}".encode()).hexdigest()[:32]

                rec = HouseholdRecommendationModel(
                    id=uuid4(),
                    home_id=home_id,
                    domain=domain,
                    title=rec_title,
                    reason=rec_reason,
                    confidence=Decimal(str(params.get("confidence", 0.90))),
                    source_category="AUTOMATION_RULE",
                    suggested_action=params.get("suggested_action"),
                    status="NEW",
                    dedup_hash=dedup_hash,
                    expires_at=datetime.now(timezone.utc) + timedelta(days=14)
                )
                db.add(rec)
                return True, str(rec.id), None

            else:
                return False, None, f"Unsupported action type '{action_type}'"

        except Exception as ex:
            logger.exception(f"Error executing action {action_type}: {ex}")
            return False, None, str(ex)
