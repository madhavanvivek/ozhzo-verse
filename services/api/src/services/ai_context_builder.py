from datetime import datetime, date, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.dependencies import HomeContext
from src.core.security_ai import sanitize_untrusted_input, demarcate_untrusted_content
from src.domain.permissions import has_permission
from src.infrastructure.database.models import (
    BillModel,
    EventModel,
    HomeMemberModel,
    HomeModel,
    InventoryItemModel,
    PurchaseItemModel,
    TaskModel,
    UserModel
)


class HouseholdContextBuilder:
    """
    Constructs a minimal, secure, role-filtered household context for AI processing.
    Guarantees strict multi-home isolation, privacy filtering, and untrusted data boundary demarcation.
    """

    @staticmethod
    async def build_context(
        db: AsyncSession, home_ctx: HomeContext
    ) -> Dict[str, Any]:
        home_id = home_ctx.home_id
        now = datetime.now(timezone.utc)
        today = date.today()

        # 1. Fetch Home Metadata
        home_stmt = select(HomeModel).where(HomeModel.id == home_id)
        home = (await db.execute(home_stmt)).scalar_one_or_none()
        home_name = sanitize_untrusted_input(home.name) if home else "Home"
        currency = home.currency if home else "INR"
        timezone_str = home.timezone if home else "Asia/Kolkata"

        # 2. Fetch Active Tasks
        task_stmt = (
            select(TaskModel)
            .where(
                TaskModel.home_id == home_id,
                TaskModel.deleted_at.is_(None),
                TaskModel.status.in_(["TODO", "IN_PROGRESS"])
            )
            .order_by(TaskModel.due_date.asc().nullslast())
            .limit(10)
        )
        tasks = (await db.execute(task_stmt)).scalars().all()
        task_dtos = [
            {
                "id": str(t.id),
                "title": sanitize_untrusted_input(t.title),
                "priority": t.priority,
                "status": t.status,
                "due_date": t.due_date.isoformat() if t.due_date else None,
                "assigned_to": str(t.assigned_to) if t.assigned_to else None
            }
            for t in tasks
        ]

        # 3. Fetch Unpaid Bills (Role-Protected: Child & Guest cannot view)
        bill_dtos: List[Dict[str, Any]] = []
        if has_permission(home_ctx.role, "bills:view"):
            bill_stmt = (
                select(BillModel)
                .where(
                    BillModel.home_id == home_id,
                    BillModel.deleted_at.is_(None),
                    BillModel.status.in_(["UNPAID", "UPCOMING", "OVERDUE"])
                )
                .order_by(BillModel.due_date.asc())
                .limit(10)
            )
            bills = (await db.execute(bill_stmt)).scalars().all()
            bill_dtos = [
                {
                    "id": str(b.id),
                    "title": sanitize_untrusted_input(b.title),
                    "amount": float(b.expected_amount),
                    "currency": b.currency,
                    "due_date": b.due_date.isoformat() if b.due_date else None,
                    "status": b.status
                }
                for b in bills
            ]


        # 4. Fetch Upcoming Events (Next 14 Days)
        event_stmt = (
            select(EventModel)
            .where(
                EventModel.home_id == home_id,
                EventModel.deleted_at.is_(None),
                EventModel.start_time >= now - timedelta(hours=2),
                EventModel.start_time <= now + timedelta(days=14)
            )
            .order_by(EventModel.start_time.asc())
            .limit(10)
        )
        events = (await db.execute(event_stmt)).scalars().all()
        event_dtos = [
            {
                "id": str(e.id),
                "title": sanitize_untrusted_input(e.title),
                "start_time": e.start_time.strftime("%d %b %H:%M"),
                "location": sanitize_untrusted_input(e.location) if e.location else None
            }
            for e in events
        ]

        # 5. Fetch Low Stock Inventory Items
        inv_stmt = (
            select(InventoryItemModel)
            .where(
                InventoryItemModel.home_id == home_id,
                InventoryItemModel.deleted_at.is_(None),
                InventoryItemModel.item_type == "CONSUMABLE",
                or_(
                    InventoryItemModel.status == "LOW_STOCK",
                    InventoryItemModel.quantity <= InventoryItemModel.min_threshold
                )
            )
            .limit(10)
        )
        low_stock_items = (await db.execute(inv_stmt)).scalars().all()
        low_stock_dtos = [
            {
                "id": str(item.id),
                "name": sanitize_untrusted_input(item.name),
                "quantity": str(item.quantity),
                "unit": item.unit,
                "status": item.status
            }
            for item in low_stock_items
        ]

        # 6. Fetch Active Shopping Items
        shop_stmt = (
            select(PurchaseItemModel)
            .where(
                PurchaseItemModel.home_id == home_id,
                PurchaseItemModel.status == "PENDING"
            )
            .limit(10)
        )
        shop_items = (await db.execute(shop_stmt)).scalars().all()
        shop_dtos = [
            {
                "id": str(s.id),
                "name": sanitize_untrusted_input(s.name),
                "quantity": str(s.quantity),
                "unit": s.unit
            }
            for s in shop_items
        ]

        # 7. Fetch Active Home Members
        mem_stmt = (
            select(HomeMemberModel)
            .options(selectinload(HomeMemberModel.user).selectinload(UserModel.profile))
            .where(
                HomeMemberModel.home_id == home_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )
        members = (await db.execute(mem_stmt)).scalars().all()
        member_dtos = [
            {
                "user_id": str(m.user_id),
                "display_name": sanitize_untrusted_input(m.user.profile.display_name) if (m.user and m.user.profile) else "Resident",
                "role": m.role
            }
            for m in members
        ]


        return {
            "home_id": str(home_id),
            "home_name": home_name,
            "currency": currency,
            "timezone": timezone_str,
            "user_role": home_ctx.role,
            "user_id": str(home_ctx.user.id),
            "user_name": getattr(home_ctx.user, "display_name", "User"),
            "tasks": task_dtos,
            "bills": bill_dtos,
            "events": event_dtos,
            "low_stock": low_stock_dtos,
            "shopping_items": shop_dtos,
            "members": member_dtos
        }
