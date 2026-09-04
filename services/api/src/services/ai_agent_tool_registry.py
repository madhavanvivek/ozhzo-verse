from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.models import (
    AutomationModel,
    BillModel,
    HouseholdRecommendationModel,
    InventoryItemModel,
    NotificationModel,
    PurchaseItemModel,
    TaskModel,
)



class ToolDefinition:
    def __init__(
        self,
        name: str,
        domain: str,
        description: str,
        permission_required: str,
        is_write_action: bool,
        input_schema: Dict[str, Any],
        handler: Callable,
    ):
        self.name = name
        self.domain = domain
        self.description = description
        self.permission_required = permission_required
        self.is_write_action = is_write_action
        self.input_schema = input_schema
        self.handler = handler


class AIAgentToolRegistry:
    """
    Allowlisted Tool Registry for Bounded AI Agent Execution.
    Guarantees that the AI agent can only invoke explicitly registered domain actions with RBAC validation.
    """

    _registry: Dict[str, ToolDefinition] = {}

    @classmethod
    def register(cls, tool: ToolDefinition):
        cls._registry[tool.name] = tool

    @classmethod
    def get_tool(cls, name: str) -> Optional[ToolDefinition]:
        return cls._registry.get(name)

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "domain": t.domain,
                "description": t.description,
                "permission_required": t.permission_required,
                "is_write_action": t.is_write_action,
                "input_schema": t.input_schema,
            }
            for t in cls._registry.values()
        ]


# ==============================================================================
# TOOL HANDLERS (READ & WRITE)
# ==============================================================================

async def _handle_query_tasks(db: AsyncSession, home_id: UUID, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    stmt = select(TaskModel).where(
        TaskModel.home_id == home_id,
        TaskModel.deleted_at.is_(None),
    )
    status_filter = params.get("status")
    if status_filter:
        stmt = stmt.where(TaskModel.status == status_filter)
    tasks = (await db.execute(stmt.limit(10))).scalars().all()
    return {
        "count": len(tasks),
        "tasks": [{"id": str(t.id), "title": t.title, "status": t.status, "due_date": str(t.due_date) if t.due_date else None} for t in tasks]
    }


async def _handle_query_bills(db: AsyncSession, home_id: UUID, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    stmt = select(BillModel).where(
        BillModel.home_id == home_id,
        BillModel.deleted_at.is_(None),
    )
    status_filter = params.get("status")
    if status_filter:
        stmt = stmt.where(BillModel.status == status_filter)
    bills = (await db.execute(stmt.limit(10))).scalars().all()
    return {
        "count": len(bills),
        "bills": [{"id": str(b.id), "title": b.title, "amount": float(b.expected_amount), "status": b.status, "due_date": str(b.due_date)} for b in bills]
    }


async def _handle_query_shopping(db: AsyncSession, home_id: UUID, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    stmt = select(PurchaseItemModel).where(
        PurchaseItemModel.home_id == home_id,
        PurchaseItemModel.status == "PENDING",
        PurchaseItemModel.deleted_at.is_(None),
    )
    items = (await db.execute(stmt.limit(15))).scalars().all()
    return {
        "count": len(items),
        "shopping_list": [{"id": str(i.id), "name": i.name, "quantity": float(i.quantity) if i.quantity else 1.0, "unit": i.unit} for i in items]
    }


async def _handle_query_inventory(db: AsyncSession, home_id: UUID, params: Dict[str, Any], **kwargs) -> Dict[str, Any]:
    stmt = select(InventoryItemModel).where(
        InventoryItemModel.home_id == home_id,
        InventoryItemModel.deleted_at.is_(None),
    )
    low_stock_only = params.get("low_stock_only", False)
    if low_stock_only:
        stmt = stmt.where(InventoryItemModel.quantity <= InventoryItemModel.min_threshold)
    items = (await db.execute(stmt.limit(15))).scalars().all()
    return {
        "count": len(items),
        "inventory": [{"id": str(i.id), "name": i.name, "quantity": float(i.quantity), "unit": i.unit, "status": i.status} for i in items]
    }


async def _handle_create_task(db: AsyncSession, home_id: UUID, params: Dict[str, Any], user_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    task = TaskModel(
        id=uuid4(),
        home_id=home_id,
        created_by=user_id,
        title=params.get("title", "New Task"),
        description=params.get("description"),
        priority=params.get("priority", "NORMAL"),
        status="TODO",
        due_date=params.get("due_date", now.date() + timedelta(days=1)),
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {"id": str(task.id), "title": task.title, "status": "CREATED"}


async def _handle_create_shopping_item(db: AsyncSession, home_id: UUID, params: Dict[str, Any], user_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    item = PurchaseItemModel(
        id=uuid4(),
        home_id=home_id,
        added_by=user_id,
        name=params.get("name", "Shopping Item"),
        quantity=Decimal(str(params.get("quantity", 1))),
        unit=params.get("unit", "pcs"),
        status="PENDING",
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return {"id": str(item.id), "name": item.name, "status": "ADDED"}


async def _handle_create_reminder(db: AsyncSession, home_id: UUID, params: Dict[str, Any], user_id: Optional[UUID] = None, **kwargs) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    if not user_id:
        return {"error": "User ID required for notification"}
    notif = NotificationModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        title=params.get("title", "Household Reminder"),
        body=params.get("body", "Scheduled reminder"),
        priority=params.get("priority", "NORMAL"),
        status="UNREAD",
        created_at=now,
        updated_at=now,
    )
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return {"id": str(notif.id), "title": notif.title, "status": "SENT"}


# Register default allowlisted tools
AIAgentToolRegistry.register(
    ToolDefinition(
        name="query_tasks",
        domain="TASK",
        description="Query household chores and tasks by status",
        permission_required="tasks:view",
        is_write_action=False,
        input_schema={"status": {"type": "string", "enum": ["TODO", "IN_PROGRESS", "COMPLETED"]}},
        handler=_handle_query_tasks,
    )
)

AIAgentToolRegistry.register(
    ToolDefinition(
        name="query_bills",
        domain="BILL",
        description="Query recurring and upcoming household bills",
        permission_required="bills:view",
        is_write_action=False,
        input_schema={"status": {"type": "string", "enum": ["UNPAID", "PAID", "UPCOMING", "OVERDUE"]}},
        handler=_handle_query_bills,
    )
)

AIAgentToolRegistry.register(
    ToolDefinition(
        name="query_shopping",
        domain="SHOPPING",
        description="Query active grocery and purchase list items",
        permission_required="shopping:view",
        is_write_action=False,
        input_schema={},
        handler=_handle_query_shopping,
    )
)

AIAgentToolRegistry.register(
    ToolDefinition(
        name="query_inventory",
        domain="INVENTORY",
        description="Query consumable stock levels in household inventory",
        permission_required="inventory:view",
        is_write_action=False,
        input_schema={"low_stock_only": {"type": "boolean"}},
        handler=_handle_query_inventory,
    )
)

AIAgentToolRegistry.register(
    ToolDefinition(
        name="create_task",
        domain="TASK",
        description="Create a new task or chore for the household",
        permission_required="tasks:create",
        is_write_action=True,
        input_schema={"title": {"type": "string"}, "priority": {"type": "string"}},
        handler=_handle_create_task,
    )
)

AIAgentToolRegistry.register(
    ToolDefinition(
        name="create_shopping_item",
        domain="SHOPPING",
        description="Add a new item to the household purchase list",
        permission_required="shopping:create",
        is_write_action=True,
        input_schema={"name": {"type": "string"}, "quantity": {"type": "number"}, "unit": {"type": "string"}},
        handler=_handle_create_shopping_item,
    )
)

AIAgentToolRegistry.register(
    ToolDefinition(
        name="create_reminder",
        domain="NOTIFICATION",
        description="Create an in-app reminder notification for a user",
        permission_required="notifications:create",
        is_write_action=True,
        input_schema={"title": {"type": "string"}, "body": {"type": "string"}, "priority": {"type": "string"}},
        handler=_handle_create_reminder,
    )
)
