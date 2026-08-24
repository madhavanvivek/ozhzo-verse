import asyncio
from datetime import date, datetime, time, timezone, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AssetLoanModel,
    BillModel,
    BillPaymentModel,
    EventModel,
    HomeModel,
    HomeMemberModel,
    InventoryItemModel,
    NotificationModel,
    PurchaseItemModel,
    StockMovementModel,
    TaskModel,
    UserModel,
    UserProfileModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.attention import AttentionItemDTO, AttentionSummaryDTO
from src.schemas.today import TodayTimelineItemDTO
from src.schemas.activity import HomeActivityItemDTO
from src.schemas.dashboard import (
    DashboardBillItemDTO,
    DashboardEventItemDTO,
    DashboardGreetingDTO,
    DashboardInventoryItemDTO,
    DashboardNotificationItemDTO,
    DashboardResponseDTO,
    DashboardShoppingItemDTO,
    DashboardSummaryDTO,
    DashboardTaskItemDTO
)

router = APIRouter(prefix="/homes/{home_id}/dashboard", tags=["Dashboard"])


def get_time_period_and_greeting(hour: int) -> tuple[str, str]:
    if 5 <= hour < 12:
        return "morning", "Good morning"
    elif 12 <= hour < 17:
        return "afternoon", "Good afternoon"
    elif 17 <= hour < 22:
        return "evening", "Good evening"
    else:
        return "night", "Good night"


def get_time_greeting(hour: int) -> str:
    return get_time_period_and_greeting(hour)[1]


def format_time_ago(dt: datetime) -> str:
    now = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff = now - dt
    seconds = int(diff.total_seconds())

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        mins = seconds // 60
        return f"{mins}m ago"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours}h ago"
    else:
        return f"{seconds // 86400}d ago"


@router.get("", response_model=ApiSuccessResponse[DashboardResponseDTO])
async def get_home_dashboard(
    home_id: Optional[UUID] = None,
    home_ctx: HomeContext = Depends(require_home_permission("dashboard:view")),
    db: AsyncSession = Depends(get_db),
):
    eff_home_id = home_id or home_ctx.home_id
    user = home_ctx.user
    role = home_ctx.role
    now = datetime.now(timezone.utc)
    today = date.today()

    # 1. Fetch Home details
    home = await db.get(HomeModel, eff_home_id)
    if not isinstance(home, HomeModel):
        try:
            q_home = select(HomeModel).where(HomeModel.id == eff_home_id, HomeModel.deleted_at.is_(None))
            fetched = (await db.execute(q_home)).scalar_one_or_none()
            if isinstance(fetched, HomeModel):
                home = fetched
            else:
                home = HomeModel(id=eff_home_id, name="Home Space", currency="INR", timezone="Asia/Kolkata")
        except Exception:
            home = HomeModel(id=eff_home_id, name="Home Space", currency="INR", timezone="Asia/Kolkata")
    if not home or home.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    # 2. Greeting
    profile_name = user.profile.display_name if (user.profile and hasattr(user.profile, "display_name") and isinstance(user.profile.display_name, str)) else (user.email.split("@")[0] if user.email else "Member")
    time_period, greeting_text = get_time_period_and_greeting(now.hour)
    date_formatted = now.strftime("%A, %d %B %Y")

    greeting_dto = DashboardGreetingDTO(
        greeting=f"{greeting_text}, {profile_name}",
        user_display_name=profile_name,
        date_formatted=date_formatted,
        time_period=time_period
    )

    # 3. Status KPI Counts
    async def _safe_execute(query):
        try:
            return await db.execute(query)
        except Exception:
            return None

    def _extract_int(val, default=0):
        if isinstance(val, int):
            return val
        return default

    def _extract_dec(val, default=Decimal("0.00")):
        if isinstance(val, (Decimal, int, float)):
            return Decimal(str(val))
        return default

    task_res = await _safe_execute(
        select(func.count()).select_from(TaskModel).where(
            TaskModel.home_id == eff_home_id, TaskModel.status.in_(["TODO", "IN_PROGRESS"]), TaskModel.deleted_at.is_(None)
        )
    )
    active_tasks_count = _extract_int(task_res.scalar_one() if (task_res and hasattr(task_res, "scalar_one")) else getattr(task_res, "scalar", lambda: 0)(), 0)

    inv_res = await _safe_execute(
        select(func.count()).select_from(InventoryItemModel).where(
            InventoryItemModel.home_id == eff_home_id,
            InventoryItemModel.item_type == "CONSUMABLE",
            InventoryItemModel.deleted_at.is_(None),
            InventoryItemModel.quantity <= InventoryItemModel.min_threshold
        )
    )
    low_stock_count = _extract_int(inv_res.scalar_one() if (inv_res and hasattr(inv_res, "scalar_one")) else getattr(inv_res, "scalar", lambda: 0)(), 0)

    bills_res = await _safe_execute(
        select(func.count(), func.coalesce(func.sum(BillModel.expected_amount - BillModel.amount_paid), Decimal("0.00")))
        .where(
            BillModel.home_id == eff_home_id,
            BillModel.deleted_at.is_(None),
            BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"])
        )
    )
    if bills_res:
        raw_bills = bills_res.first() if hasattr(bills_res, "first") else (bills_res.one() if hasattr(bills_res, "one") else None)
        if raw_bills and isinstance(raw_bills, (tuple, list)):
            unpaid_bills_count = _extract_int(raw_bills[0], 0)
            unpaid_bills_sum = _extract_dec(raw_bills[1], Decimal("0.00"))
        else:
            unpaid_bills_count = _extract_int(getattr(raw_bills, "scalar", lambda: 0)(), 0)
            unpaid_bills_sum = Decimal("0.00")
    else:
        unpaid_bills_count = 0
        unpaid_bills_sum = Decimal("0.00")

    mem_res = await _safe_execute(
        select(func.count()).select_from(HomeMemberModel).where(
            HomeMemberModel.home_id == eff_home_id, HomeMemberModel.status == "ACTIVE"
        )
    )
    members_count = _extract_int(mem_res.scalar_one() if (mem_res and hasattr(mem_res, "scalar_one")) else getattr(mem_res, "scalar", lambda: 0)(), 0)

    if role in ("CHILD", "GUEST"):
        unpaid_bills_count = 0
        unpaid_bills_sum = Decimal("0.00")
        borrowed_assets_count = 0
    else:
        asset_res = await _safe_execute(
            select(func.count()).select_from(AssetLoanModel).where(
                AssetLoanModel.home_id == eff_home_id, AssetLoanModel.loan_status == "ACTIVE"
            )
        )
        borrowed_assets_count = _extract_int(asset_res.scalar_one() if (asset_res and hasattr(asset_res, "scalar_one")) else getattr(asset_res, "scalar", lambda: 0)(), 0)

    pur_res = await _safe_execute(
        select(func.count()).select_from(PurchaseItemModel).where(
            PurchaseItemModel.home_id == eff_home_id,
            PurchaseItemModel.status == "PENDING",
            PurchaseItemModel.deleted_at.is_(None)
        )
    )
    purchase_items_count = _extract_int(pur_res.scalar_one() if (pur_res and hasattr(pur_res, "scalar_one")) else getattr(pur_res, "scalar", lambda: 0)(), 0)

    evt_res = await _safe_execute(
        select(func.count()).select_from(EventModel).where(
            EventModel.home_id == eff_home_id,
            EventModel.start_time >= now - timedelta(hours=2),
            EventModel.deleted_at.is_(None)
        )
    )
    upcoming_events_count = _extract_int(evt_res.scalar_one() if (evt_res and hasattr(evt_res, "scalar_one")) else getattr(evt_res, "scalar", lambda: 0)(), 0)

    summary_dto = DashboardSummaryDTO(
        home_id=home.id,
        home_name=home.name,
        currency=home.currency or "INR",
        timezone=home.timezone or "Asia/Kolkata",
        members_count=members_count,
        active_tasks_count=active_tasks_count,
        low_stock_count=low_stock_count,
        unpaid_bills_count=unpaid_bills_count,
        unpaid_bills_sum=unpaid_bills_sum,
        purchase_items_count=purchase_items_count,
        borrowed_assets_count=borrowed_assets_count,
        upcoming_events_count=upcoming_events_count,
        unread_notifications_count=0
    )

    # 4. Attention Items (Ranked by Severity)
    attention_items: List[AttentionItemDTO] = []

    # 4a. Overdue Bills (Critical)
    if role not in ("CHILD", "GUEST"):
        bills_res = await _safe_execute(
            select(BillModel).where(
                BillModel.home_id == eff_home_id,
                BillModel.deleted_at.is_(None),
                BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]),
                BillModel.due_date < today
            ).order_by(BillModel.due_date.asc()).limit(3)
        )
        overdue_bills = bills_res.scalars().all() if bills_res else []
        for b in overdue_bills:
            if isinstance(b, BillModel):
                rem_balance = max(0, b.expected_amount - b.amount_paid)
                attention_items.append(
                    AttentionItemDTO(
                        id=b.id,
                        severity="CRITICAL",
                        category="BILL_OVERDUE",
                        title=f"Overdue Bill: {b.title}",
                        subtitle=f"{b.currency} {rem_balance:.2f} overdue since {b.due_date}",
                        action_label="Record Payment",
                        navigation_target=f"/bills/{b.id}"
                    )
                )

    # 4b. Overdue Tasks (Critical)
    tasks_res = await _safe_execute(
        select(TaskModel).where(
            TaskModel.home_id == eff_home_id,
            TaskModel.deleted_at.is_(None),
            TaskModel.status.in_(["TODO", "IN_PROGRESS"]),
            TaskModel.due_date < today
        ).order_by(TaskModel.due_date.asc()).limit(3)
    )
    overdue_tasks = tasks_res.scalars().all() if tasks_res else []
    for t in overdue_tasks:
        if isinstance(t, TaskModel):
            attention_items.append(
                AttentionItemDTO(
                    id=t.id,
                    severity="CRITICAL",
                    category="TASK_OVERDUE",
                    title=f"Overdue Chore: {t.title}",
                    subtitle=f"Was due on {t.due_date}",
                    action_label="Complete",
                    navigation_target=f"/tasks/{t.id}"
                )
            )

    # 4c. Out of Stock Supplies (High)
    inv_res = await _safe_execute(
        select(InventoryItemModel).where(
            InventoryItemModel.home_id == eff_home_id,
            InventoryItemModel.deleted_at.is_(None),
            InventoryItemModel.item_type == "CONSUMABLE",
            InventoryItemModel.quantity <= 0
        ).limit(3)
    )
    out_stock = inv_res.scalars().all() if inv_res else []
    for i in out_stock:
        if isinstance(i, InventoryItemModel):
            attention_items.append(
                AttentionItemDTO(
                    id=i.id,
                    severity="HIGH",
                    category="STOCK_EMPTY",
                    title=f"Out of Stock: {i.name}",
                    subtitle=f"0 {i.unit} left",
                    action_label="Restock",
                    navigation_target=f"/inventory/{i.id}"
                )
            )

    critical_c = sum(1 for i in attention_items if i.severity == "CRITICAL")
    high_c = sum(1 for i in attention_items if i.severity == "HIGH")

    attention_summary = AttentionSummaryDTO(
        critical_count=critical_c,
        high_count=high_c,
        normal_count=0,
        info_count=0,
        total_attention_items=len(attention_items)
    )

    # 5. Today Pulse
    today_start = datetime.combine(today, time.min, tzinfo=timezone.utc)
    today_end = datetime.combine(today, time.max, tzinfo=timezone.utc)
    today_timeline: List[TodayTimelineItemDTO] = []

    # Events Today
    evts_res = await _safe_execute(
        select(EventModel).where(
            EventModel.home_id == eff_home_id,
            EventModel.deleted_at.is_(None),
            EventModel.start_time <= today_end,
            EventModel.end_time >= today_start
        ).order_by(EventModel.start_time.asc()).limit(5)
    )
    evts = evts_res.scalars().all() if evts_res else []
    for e in evts:
        if isinstance(e, EventModel):
            today_timeline.append(
                TodayTimelineItemDTO(
                    id=e.id,
                    source_type="EVENT",
                    source_id=e.id,
                    title=e.title,
                    start=e.start_time,
                    end=e.end_time,
                    all_day=e.is_all_day,
                    status=e.status,
                    navigation_target=f"/calendar/{e.id}",
                    location=e.location
                )
            )

    # Tasks Due Today
    tsks_res = await _safe_execute(
        select(TaskModel).where(
            TaskModel.home_id == eff_home_id,
            TaskModel.deleted_at.is_(None),
            TaskModel.status != "COMPLETED",
            TaskModel.due_date == today
        ).limit(5)
    )
    tsks = tsks_res.scalars().all() if tsks_res else []
    for t in tsks:
        if isinstance(t, TaskModel):
            t_dt = datetime.combine(today, time(18, 0), tzinfo=timezone.utc)
            today_timeline.append(
                TodayTimelineItemDTO(
                    id=t.id,
                    source_type="TASK",
                    source_id=t.id,
                    title=t.title,
                    start=t_dt,
                    end=t_dt,
                    priority=t.priority,
                    status=t.status,
                    navigation_target=f"/tasks/{t.id}"
                )
            )

    # 6. Recent Activity (Last 5)
    recent_activity: List[HomeActivityItemDTO] = []
    moves_res = await _safe_execute(
        select(StockMovementModel).options(selectinload(StockMovementModel.item))
        .where(StockMovementModel.home_id == eff_home_id)
        .order_by(StockMovementModel.created_at.desc()).limit(3)
    )
    stock_moves = moves_res.scalars().all() if moves_res else []
    for s in stock_moves:
        item_name = s.item.name if s.item else "Supplies"
        action_verb = "added" if s.movement_type == "RESTOCK" else "consumed"
        recent_activity.append(
            HomeActivityItemDTO(
                id=s.id,
                activity_type="STOCK_MOVE",
                title=f"{item_name} Updated",
                description=f"Supplies {action_verb} {abs(s.quantity_delta)} {s.item.unit if s.item else ''}",
                actor_id=s.performed_by,
                actor_name="Member",
                timestamp=s.created_at,
                time_ago=format_time_ago(s.created_at),
                navigation_target=f"/inventory/{s.item_id}"
            )
        )

    payments_res = await _safe_execute(
        select(BillPaymentModel).options(selectinload(BillPaymentModel.bill), selectinload(BillPaymentModel.payer))
        .where(BillPaymentModel.home_id == eff_home_id)
        .order_by(BillPaymentModel.created_at.desc()).limit(2)
    )
    bill_payments = payments_res.scalars().all() if payments_res else []
    for bp in bill_payments:
        bill_title = bp.bill.title if bp.bill else "Bill"
        actor_name = bp.payer.profile.display_name if (bp.payer and bp.payer.profile) else "Member"
        recent_activity.append(
            HomeActivityItemDTO(
                id=bp.id,
                activity_type="BILL_PAID",
                title="Payment Recorded",
                description=f'{actor_name} paid {bp.currency} {bp.amount_paid:.2f} for "{bill_title}"',
                actor_id=bp.paid_by,
                actor_name=actor_name,
                timestamp=bp.created_at,
                time_ago=format_time_ago(bp.created_at),
                navigation_target=f"/bills/{bp.bill_id}"
            )
        )

    recent_activity.sort(key=lambda x: x.timestamp, reverse=True)

    return ApiSuccessResponse(
        data=DashboardResponseDTO(
            greeting=greeting_dto,
            summary=summary_dto,
            attention_summary=attention_summary,
            attention_items=attention_items,
            today_timeline=today_timeline,
            recent_activity=recent_activity[:5],
            pending_tasks=[],
            upcoming_bills=[],
            upcoming_events=[],
            low_stock_inventory=[],
            shopping_items=[],
            notifications=[],
            role=role
        )
    )
