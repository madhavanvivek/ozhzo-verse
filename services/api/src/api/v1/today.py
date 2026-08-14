from datetime import date, datetime, time, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AssetLoanModel,
    BillModel,
    EventModel,
    HomeModel,
    InventoryItemModel,
    PurchaseItemModel,
    TaskModel
)
from src.schemas.today import (
    TodayResponseDTO,
    TodaySummaryDTO,
    TodayTimelineItemDTO
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/homes/{home_id}/today", tags=["Today View"])


@router.get("", response_model=ApiSuccessResponse[TodayResponseDTO])
async def get_unified_today_view(
    timezone_name: Optional[str] = Query(None, description="Client timezone"),
    home_ctx: HomeContext = Depends(require_home_permission("homes:view")),
    db: AsyncSession = Depends(get_db),
):
    home = await db.get(HomeModel, home_ctx.home_id)
    tz = timezone_name or (home.timezone if home else "UTC")
    today = date.today()
    start_today = datetime.combine(today, time.min, tzinfo=timezone.utc)
    end_today = datetime.combine(today, time.max, tzinfo=timezone.utc)

    timeline: List[TodayTimelineItemDTO] = []
    attention_alerts: List[TodayTimelineItemDTO] = []

    # 1. Events Today
    events_q = (
        select(EventModel)
        .options(selectinload(EventModel.category))
        .where(
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None),
            EventModel.start_time <= end_today,
            EventModel.end_time >= start_today
        )
        .order_by(EventModel.start_time.asc())
    )
    events = (await db.execute(events_q)).scalars().all()
    for e in events:
        timeline.append(
            TodayTimelineItemDTO(
                id=e.id,
                source_type="EVENT",
                source_id=e.id,
                title=e.title,
                start=e.start_time,
                end=e.end_time,
                all_day=e.is_all_day,
                priority="NORMAL",
                status=e.status,
                navigation_target=f"/calendar/{e.id}",
                category_name=e.category.name if e.category else None,
                location=e.location,
                meta_info={"description": e.description}
            )
        )

    # 2. Tasks Due Today
    tasks_q = (
        select(TaskModel)
        .options(selectinload(TaskModel.category), selectinload(TaskModel.assignee))
        .where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.deleted_at.is_(None),
            TaskModel.status != "COMPLETED",
            TaskModel.due_date == today
        )
    )
    tasks = (await db.execute(tasks_q)).scalars().all()
    for t in tasks:
        task_dt = datetime.combine(today, time(18, 0), tzinfo=timezone.utc)
        timeline.append(
            TodayTimelineItemDTO(
                id=t.id,
                source_type="TASK",
                source_id=t.id,
                title=f"Task: {t.title}",
                start=task_dt,
                end=task_dt,
                all_day=False,
                priority=t.priority,
                status=t.status,
                navigation_target=f"/tasks/{t.id}",
                category_name=t.category.name if t.category else None,
                meta_info={"assigned_to": str(t.assigned_to) if t.assigned_to else None}
            )
        )

    # 3. Bills Due Today
    bills_q = (
        select(BillModel)
        .options(selectinload(BillModel.category))
        .where(
            BillModel.home_id == home_ctx.home_id,
            BillModel.deleted_at.is_(None),
            BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]),
            BillModel.due_date == today
        )
    )
    bills = (await db.execute(bills_q)).scalars().all()
    for b in bills:
        bill_dt = datetime.combine(today, time(23, 59, 59), tzinfo=timezone.utc)
        rem_balance = max(0, b.expected_amount - b.amount_paid)
        timeline.append(
            TodayTimelineItemDTO(
                id=b.id,
                source_type="BILL",
                source_id=b.id,
                title=f"Bill Due: {b.title} ({b.currency} {rem_balance:.2f})",
                start=bill_dt,
                end=bill_dt,
                all_day=True,
                priority="HIGH",
                status=b.status,
                navigation_target=f"/bills/{b.id}",
                category_name=b.category.name if b.category else None,
                meta_info={"expected_amount": str(b.expected_amount), "remaining_balance": str(rem_balance)}
            )
        )

    # 4. Urgent Purchases (Attention Alerts)
    purchases_q = (
        select(PurchaseItemModel)
        .where(
            PurchaseItemModel.home_id == home_ctx.home_id,
            PurchaseItemModel.is_checked == False,
            PurchaseItemModel.priority.in_(["HIGH", "URGENT"])
        )
    )
    purchases = (await db.execute(purchases_q)).scalars().all()
    for p in purchases:
        p_dt = datetime.combine(today, time(12, 0), tzinfo=timezone.utc)
        attention_alerts.append(
            TodayTimelineItemDTO(
                id=p.id,
                source_type="PURCHASE",
                source_id=p.id,
                title=f"Urgent Need: {p.name} ({p.quantity} {p.unit})",
                start=p_dt,
                end=p_dt,
                all_day=True,
                priority="HIGH",
                status="UNCHECKED",
                navigation_target="/purchase-list",
                meta_info={"quantity": str(p.quantity), "unit": p.unit}
            )
        )

    # 5. Out of Stock Inventory Supplies
    out_stock_q = (
        select(InventoryItemModel)
        .where(
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at.is_(None),
            InventoryItemModel.item_type == "CONSUMABLE",
            InventoryItemModel.quantity <= 0
        )
    )
    out_stock = (await db.execute(out_stock_q)).scalars().all()
    for i in out_stock:
        i_dt = datetime.combine(today, time(8, 0), tzinfo=timezone.utc)
        attention_alerts.append(
            TodayTimelineItemDTO(
                id=i.id,
                source_type="INVENTORY",
                source_id=i.id,
                title=f"Empty Stock: {i.name}",
                start=i_dt,
                end=i_dt,
                all_day=True,
                priority="HIGH",
                status="OUT_OF_STOCK",
                navigation_target=f"/inventory/{i.id}",
                meta_info={"unit": i.unit, "location_path": i.location_path}
            )
        )

    # Sort timeline chronologically
    timeline.sort(key=lambda x: x.start)

    summary = TodaySummaryDTO(
        total_items=len(timeline) + len(attention_alerts),
        events_count=len(events),
        tasks_count=len(tasks),
        bills_count=len(bills),
        purchase_urgent_count=len(purchases),
        inventory_alerts_count=len(out_stock)
    )

    return ApiSuccessResponse(
        data=TodayResponseDTO(
            date=today.isoformat(),
            timezone=tz,
            summary=summary,
            timeline=timeline,
            attention_alerts=attention_alerts
        )
    )
