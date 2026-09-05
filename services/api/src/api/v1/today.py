from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID
import zoneinfo
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AssetLoanModel,
    BillModel,
    EventModel,
    HomeModel,
    HomeMemberModel,
    InvitationModel,
    InventoryItemModel,
    NotificationModel,
    PurchaseItemModel,
    TaskModel,
    UserModel
)
from src.schemas.today import (
    TodayAttentionItemDTO,
    TodayBillsSectionDTO,
    TodayCalendarSectionDTO,
    TodayFamilySectionDTO,
    TodayInventorySectionDTO,
    TodayNotificationsSectionDTO,
    TodayResponseDTO,
    TodayShoppingSectionDTO,
    TodaySummaryDTO,
    TodayTasksSectionDTO,
    TodayTimelineItemDTO
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/homes/{home_id}/today", tags=["Today View"])


def resolve_home_timezone(tz_name: Optional[str]) -> tuple[zoneinfo.ZoneInfo, str]:
    if not tz_name:
        return zoneinfo.ZoneInfo("UTC"), "UTC"
    try:
        return zoneinfo.ZoneInfo(tz_name), tz_name
    except Exception:
        return zoneinfo.ZoneInfo("UTC"), "UTC"


@router.get("", response_model=ApiSuccessResponse[TodayResponseDTO])
async def get_unified_today_view(
    timezone_name: Optional[str] = Query(None, description="Client timezone"),
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    home = await db.get(HomeModel, home_ctx.home_id)
    tz_info, tz_str = resolve_home_timezone(timezone_name or (home.timezone if home else "UTC"))
    
    # Calculate timezone-aware dates
    now_local = datetime.now(tz_info)
    today = now_local.date()
    start_today_local = datetime.combine(today, time.min)
    end_today_local = datetime.combine(today, time.max)
    start_today_utc = start_today_local.replace(tzinfo=tz_info).astimezone(timezone.utc)
    end_today_utc = end_today_local.replace(tzinfo=tz_info).astimezone(timezone.utc)
    horizon_date = today + timedelta(days=7)
    horizon_utc = datetime.combine(horizon_date, time.max).replace(tzinfo=tz_info).astimezone(timezone.utc)

    # -------------------------------------------------------------------------
    # 1. TASKS AGGREGATION
    # -------------------------------------------------------------------------
    tasks_q = (
        select(TaskModel)
        .options(joinedload(TaskModel.category))
        .where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.deleted_at.is_(None),
            TaskModel.status != "COMPLETED"
        )
        .order_by(TaskModel.due_date.asc().nulls_last(), TaskModel.created_at.desc())
    )
    tasks_res = await db.execute(tasks_q)
    tasks = tasks_res.scalars().all()

    overdue_tasks: List[TodayAttentionItemDTO] = []
    due_today_tasks: List[TodayAttentionItemDTO] = []
    my_tasks: List[TodayAttentionItemDTO] = []
    family_tasks: List[TodayAttentionItemDTO] = []
    upcoming_tasks: List[TodayAttentionItemDTO] = []

    for t in tasks:
        is_my_task = (t.assigned_to == home_ctx.user.id)
        t_date = t.due_date.date() if isinstance(t.due_date, datetime) else t.due_date
        t_due_time = t.due_date if isinstance(t.due_date, datetime) else (
            datetime.combine(t.due_date, time(18, 0), tzinfo=timezone.utc) if t.due_date else None
        )

        item_priority = "NORMAL"
        badge = None
        if t_date:
            if t_date < today:
                days_overdue = (today - t_date).days
                item_priority = "CRITICAL" if t.priority in ["HIGH", "URGENT"] else "HIGH"
                badge = f"Overdue ({days_overdue}d)"
            elif t_date == today:
                item_priority = "HIGH"
                badge = "Due Today"
            elif t_date <= horizon_date:
                days_ahead = (t_date - today).days
                item_priority = "NORMAL"
                badge = f"Due in {days_ahead}d"

        task_dto = TodayAttentionItemDTO(
            id=t.id,
            source_type="TASK",
            source_id=t.id,
            title=t.title,
            subtitle=f"Category: {t.category.name}" if t.category else None,
            priority=item_priority,
            badge_text=badge,
            due_date=t_date.isoformat() if t_date else None,
            due_time=t_due_time,
            navigation_target=f"/tasks?task_id={t.id}",
            status=t.status,
            category_name=t.category.name if t.category else None,
            assignee_id=t.assigned_to,
            is_assigned_to_me=is_my_task,
            meta_info={"priority_label": t.priority, "has_bill": bool(getattr(t, "bill_id", None))}
        )

        if t_date:
            if t_date < today:
                overdue_tasks.append(task_dto)
            elif t_date == today:
                due_today_tasks.append(task_dto)
            elif t_date <= horizon_date:
                upcoming_tasks.append(task_dto)

        if is_my_task:
            my_tasks.append(task_dto)
        else:
            family_tasks.append(task_dto)

    # Completed tasks today count
    completed_today_q = select(func.count(TaskModel.id)).where(
        TaskModel.home_id == home_ctx.home_id,
        TaskModel.deleted_at.is_(None),
        TaskModel.status == "COMPLETED",
        func.date(TaskModel.updated_at) == today
    )
    completed_today_count = (await db.execute(completed_today_q)).scalar() or 0

    tasks_section = TodayTasksSectionDTO(
        overdue=overdue_tasks,
        due_today=due_today_tasks,
        my_tasks=my_tasks,
        family_tasks=family_tasks,
        upcoming=upcoming_tasks,
        completed_today_count=completed_today_count
    )

    # -------------------------------------------------------------------------
    # 2. BILLS AGGREGATION
    # -------------------------------------------------------------------------
    bills_q = (
        select(BillModel)
        .options(joinedload(BillModel.category))
        .where(
            BillModel.home_id == home_ctx.home_id,
            BillModel.deleted_at.is_(None),
            BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]),
            (BillModel.expected_amount - BillModel.amount_paid) > 0
        )
        .order_by(BillModel.due_date.asc())
    )
    bills_res = await db.execute(bills_q)
    bills = bills_res.scalars().all()

    overdue_bills: List[TodayAttentionItemDTO] = []
    due_today_bills: List[TodayAttentionItemDTO] = []
    upcoming_bills: List[TodayAttentionItemDTO] = []
    total_due_today_amount = 0.0

    for b in bills:
        rem_balance = float(max(0, b.expected_amount - (b.amount_paid or 0)))
        if rem_balance <= 0 or b.status == "PAID":
            continue

        b_due_time = datetime.combine(b.due_date, time(23, 59, 59), tzinfo=timezone.utc)

        item_priority = "NORMAL"
        badge = None
        if b.due_date < today:
            days_overdue = (today - b.due_date).days
            item_priority = "CRITICAL"
            badge = f"Overdue ({days_overdue}d)"
        elif b.due_date == today:
            item_priority = "HIGH"
            badge = "Due Today"
            total_due_today_amount += rem_balance
        elif b.due_date <= horizon_date:
            days_ahead = (b.due_date - today).days
            item_priority = "NORMAL"
            badge = f"Due in {days_ahead}d"

        bill_dto = TodayAttentionItemDTO(
            id=b.id,
            source_type="BILL",
            source_id=b.id,
            title=b.title,
            subtitle=f"{b.currency} {rem_balance:.2f} remaining" if b.currency else f"{rem_balance:.2f}",
            priority=item_priority,
            badge_text=badge,
            due_date=b.due_date.isoformat(),
            due_time=b_due_time,
            navigation_target=f"/bills?bill_id={b.id}",
            amount=rem_balance,
            currency=b.currency,
            status=b.status,
            category_name=b.category.name if b.category else None,
            meta_info={"recurrence_type": b.recurrence_type, "total_expected": float(b.expected_amount)}
        )

        if b.due_date < today:
            overdue_bills.append(bill_dto)
        elif b.due_date == today:
            due_today_bills.append(bill_dto)
        elif b.due_date <= horizon_date:
            upcoming_bills.append(bill_dto)

    bills_section = TodayBillsSectionDTO(
        overdue=overdue_bills,
        due_today=due_today_bills,
        upcoming=upcoming_bills,
        total_due_today_amount=round(total_due_today_amount, 2),
        currency=home.currency if home else "USD"
    )

    # -------------------------------------------------------------------------
    # 3. CALENDAR EVENTS AGGREGATION
    # -------------------------------------------------------------------------
    events_q = (
        select(EventModel)
        .options(joinedload(EventModel.category))
        .where(
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None),
            EventModel.start_time <= horizon_utc,
            EventModel.end_time >= start_today_utc
        )
        .order_by(EventModel.start_time.asc())
    )
    events_res = await db.execute(events_q)
    events = events_res.scalars().all()

    today_events: List[TodayAttentionItemDTO] = []
    upcoming_events: List[TodayAttentionItemDTO] = []

    for e in events:
        is_today = (e.start_time <= end_today_utc and e.end_time >= start_today_utc)
        item_priority = "HIGH" if is_today else "NORMAL"
        badge = "Today" if is_today else "Upcoming"

        event_dto = TodayAttentionItemDTO(
            id=e.id,
            source_type="EVENT",
            source_id=e.id,
            title=e.title,
            subtitle=e.description,
            priority=item_priority,
            badge_text=badge,
            due_time=e.start_time,
            navigation_target=f"/calendar?event_id={e.id}",
            status=e.status,
            category_name=e.category.name if e.category else None,
            location=e.location,
            meta_info={"is_all_day": e.is_all_day, "start": e.start_time.isoformat(), "end": e.end_time.isoformat()}
        )

        if is_today:
            today_events.append(event_dto)
        else:
            upcoming_events.append(event_dto)

    calendar_section = TodayCalendarSectionDTO(
        today_events=today_events,
        upcoming_events=upcoming_events
    )

    # -------------------------------------------------------------------------
    # 4. INVENTORY ALERTS AGGREGATION
    # -------------------------------------------------------------------------
    inventory_q = (
        select(InventoryItemModel)
        .where(
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at.is_(None)
        )
    )
    inventory_res = await db.execute(inventory_q)
    inventory_items = inventory_res.scalars().all()

    out_of_stock: List[TodayAttentionItemDTO] = []
    low_stock: List[TodayAttentionItemDTO] = []
    expiring_soon: List[TodayAttentionItemDTO] = []

    for inv in inventory_items:
        threshold = inv.min_threshold if inv.min_threshold is not None else 1
        if inv.quantity <= 0:
            out_of_stock.append(
                TodayAttentionItemDTO(
                    id=inv.id,
                    source_type="INVENTORY",
                    source_id=inv.id,
                    title=f"Out of Stock: {inv.name}",
                    subtitle=f"Location: {inv.location_path}" if inv.location_path else None,
                    priority="CRITICAL",
                    badge_text="Out of Stock",
                    navigation_target=f"/inventory?item_id={inv.id}",
                    status="OUT_OF_STOCK",
                    location=inv.location_path,
                    meta_info={"unit": inv.unit, "quantity": inv.quantity}
                )
            )
        elif inv.quantity <= threshold:
            low_stock.append(
                TodayAttentionItemDTO(
                    id=inv.id,
                    source_type="INVENTORY",
                    source_id=inv.id,
                    title=f"Low Stock: {inv.name}",
                    subtitle=f"Remaining: {inv.quantity} {inv.unit or 'units'} (Min: {threshold})",
                    priority="HIGH",
                    badge_text="Low Stock",
                    navigation_target=f"/inventory?item_id={inv.id}",
                    status="LOW_STOCK",
                    location=inv.location_path,
                    meta_info={"unit": inv.unit, "quantity": inv.quantity, "threshold": threshold}
                )
            )

        if inv.expiry_date and inv.expiry_date <= horizon_date:
            is_expired = inv.expiry_date < today
            exp_prio = "CRITICAL" if is_expired else "HIGH"
            exp_badge = "Expired" if is_expired else f"Expires in {(inv.expiry_date - today).days}d"
            expiring_soon.append(
                TodayAttentionItemDTO(
                    id=inv.id,
                    source_type="INVENTORY",
                    source_id=inv.id,
                    title=f"{'Expired' if is_expired else 'Expiring Soon'}: {inv.name}",
                    subtitle=f"Expiry Date: {inv.expiry_date.isoformat()}",
                    priority=exp_prio,
                    badge_text=exp_badge,
                    due_date=inv.expiry_date.isoformat(),
                    navigation_target=f"/inventory?item_id={inv.id}",
                    status="EXPIRED" if is_expired else "EXPIRING_SOON",
                    location=inv.location_path,
                    meta_info={"expiry_date": inv.expiry_date.isoformat()}
                )
            )

    inventory_section = TodayInventorySectionDTO(
        out_of_stock=out_of_stock,
        low_stock=low_stock,
        expiring_soon=expiring_soon
    )

    # -------------------------------------------------------------------------
    # 5. SHOPPING / PURCHASE LIST AGGREGATION
    # -------------------------------------------------------------------------
    purchases_q = (
        select(PurchaseItemModel)
        .where(
            PurchaseItemModel.home_id == home_ctx.home_id,
            PurchaseItemModel.deleted_at.is_(None),
            PurchaseItemModel.status == "PENDING"
        )
        .order_by(PurchaseItemModel.created_at.desc())
    )
    purchases_res = await db.execute(purchases_q)
    purchases = purchases_res.scalars().all()

    urgent_shopping: List[TodayAttentionItemDTO] = []
    pending_shopping: List[TodayAttentionItemDTO] = []

    for p in purchases:
        p_qty = float(p.quantity) if p.quantity is not None else 1.0
        shop_dto = TodayAttentionItemDTO(
            id=p.id,
            source_type="PURCHASE",
            source_id=p.id,
            title=p.name,
            subtitle=f"{p_qty:g} {p.unit or 'items'}" if p.quantity else None,
            priority="NORMAL",
            badge_text="Pending",
            navigation_target="/purchase-list",
            status="PENDING",
            meta_info={"quantity": p_qty, "unit": p.unit}
        )
        pending_shopping.append(shop_dto)

    shopping_section = TodayShoppingSectionDTO(
        urgent_items=urgent_shopping,
        pending_items=pending_shopping,
        total_pending_count=len(purchases)
    )

    # -------------------------------------------------------------------------
    # 6. FAMILY & MEMBERSHIP WORKLOAD
    # -------------------------------------------------------------------------
    members_q = (
        select(HomeMemberModel)
        .options(joinedload(HomeMemberModel.user))
        .where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.status == "ACTIVE"
        )
    )
    members_res = await db.execute(members_q)
    members = members_res.scalars().all()

    invitations_q = (
        select(func.count(InvitationModel.id))
        .where(
            InvitationModel.home_id == home_ctx.home_id,
            InvitationModel.status == "PENDING"
        )
    )
    pending_invites_count = (await db.execute(invitations_q)).scalar() or 0

    member_workloads: List[Dict[str, Any]] = []
    for m in members:
        user_name = m.user.profile.display_name if m.user and m.user.profile and m.user.profile.display_name else (
            m.user.email if m.user else "Household Member"
        )
        # Count active open tasks assigned to this member
        member_open_tasks = sum(1 for t in tasks if t.assigned_to == m.user_id)
        member_workloads.append({
            "member_id": str(m.id),
            "user_id": str(m.user_id),
            "display_name": user_name,
            "role": m.role,
            "open_tasks_count": member_open_tasks,
            "is_current_user": bool(m.user_id == home_ctx.user.id)
        })

    family_section = TodayFamilySectionDTO(
        active_members_count=len(members),
        pending_invitations_count=pending_invites_count,
        member_workloads=member_workloads
    )

    # -------------------------------------------------------------------------
    # 7. NOTIFICATIONS AGGREGATION
    # -------------------------------------------------------------------------
    notifs_q = (
        select(NotificationModel)
        .where(
            NotificationModel.home_id == home_ctx.home_id,
            NotificationModel.user_id == home_ctx.user.id,
            NotificationModel.is_read == False
        )
        .order_by(NotificationModel.created_at.desc())
        .limit(10)
    )
    notifs_res = await db.execute(notifs_q)
    notifications = notifs_res.scalars().all()

    important_alerts: List[TodayAttentionItemDTO] = []
    for n in notifications:
        important_alerts.append(
            TodayAttentionItemDTO(
                id=n.id,
                source_type="NOTIFICATION",
                source_id=n.id,
                title=n.title,
                subtitle=n.body,
                priority="HIGH" if "urgent" in n.type.lower() or "alert" in n.type.lower() else "NORMAL",
                badge_text="Notification",
                navigation_target="/notifications",
                status="UNREAD",
                due_time=n.created_at,
                meta_info={"type": n.type}
            )
        )

    notifications_section = TodayNotificationsSectionDTO(
        unread_count=len(notifications),
        important_alerts=important_alerts
    )

    # -------------------------------------------------------------------------
    # 8. UNIFIED "NEEDS ATTENTION" PRIORITY ROLLUP
    # -------------------------------------------------------------------------
    needs_attention: List[TodayAttentionItemDTO] = []
    needs_attention.extend(overdue_bills)
    needs_attention.extend(overdue_tasks)
    needs_attention.extend(out_of_stock)
    needs_attention.extend(due_today_bills)
    needs_attention.extend(due_today_tasks)
    needs_attention.extend(low_stock)
    needs_attention.extend([i for i in expiring_soon if i.priority in ["CRITICAL", "HIGH"]])
    needs_attention.extend(urgent_shopping)

    # Sort: CRITICAL first, then HIGH, then NORMAL
    prio_order = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2, "LOW": 3}
    needs_attention.sort(key=lambda x: prio_order.get(x.priority, 99))

    # Calculate summary numbers
    critical_count = sum(1 for item in needs_attention if item.priority == "CRITICAL")
    high_count = sum(1 for item in needs_attention if item.priority == "HIGH")
    normal_count = len(upcoming_tasks) + len(upcoming_bills) + len(upcoming_events) + len(pending_shopping)
    low_count = completed_today_count

    summary = TodaySummaryDTO(
        total_items=len(needs_attention) + normal_count,
        critical_count=critical_count,
        high_count=high_count,
        normal_count=normal_count,
        low_count=low_count,
        events_count=len(today_events) + len(upcoming_events),
        tasks_count=len(tasks),
        bills_count=len(bills),
        purchase_urgent_count=len(urgent_shopping),
        inventory_alerts_count=len(out_of_stock) + len(low_stock)
    )

    # -------------------------------------------------------------------------
    # 9. BACKWARD-COMPATIBLE TIMELINE STREAM & ATTENTION ALERTS
    # -------------------------------------------------------------------------
    timeline: List[TodayTimelineItemDTO] = []
    for e in today_events:
        timeline.append(
            TodayTimelineItemDTO(
                id=e.id,
                source_type="EVENT",
                source_id=e.source_id,
                title=e.title,
                start=e.due_time or start_today_utc,
                end=e.due_time or end_today_utc,
                all_day=e.meta_info.get("is_all_day", False) if e.meta_info else False,
                priority=e.priority,
                status=e.status or "SCHEDULED",
                navigation_target=e.navigation_target,
                category_name=e.category_name,
                location=e.location,
                meta_info=e.meta_info
            )
        )
    for t in due_today_tasks:
        t_dt = t.due_time or datetime.combine(today, time(18, 0), tzinfo=timezone.utc)
        timeline.append(
            TodayTimelineItemDTO(
                id=t.id,
                source_type="TASK",
                source_id=t.source_id,
                title=f"Task: {t.title}",
                start=t_dt,
                end=t_dt,
                all_day=False,
                priority=t.priority,
                status=t.status or "TODO",
                navigation_target=t.navigation_target,
                category_name=t.category_name,
                meta_info=t.meta_info
            )
        )
    for b in due_today_bills:
        b_dt = b.due_time or datetime.combine(today, time(23, 59, 59), tzinfo=timezone.utc)
        timeline.append(
            TodayTimelineItemDTO(
                id=b.id,
                source_type="BILL",
                source_id=b.source_id,
                title=f"Bill Due: {b.title} ({b.currency} {b.amount:.2f})",
                start=b_dt,
                end=b_dt,
                all_day=True,
                priority="HIGH",
                status=b.status or "UNPAID",
                navigation_target=b.navigation_target,
                category_name=b.category_name,
                meta_info=b.meta_info
            )
        )
    timeline.sort(key=lambda x: x.start)

    legacy_attention: List[TodayTimelineItemDTO] = []
    for item in needs_attention[:10]:
        item_dt = item.due_time or datetime.combine(today, time(12, 0), tzinfo=timezone.utc)
        legacy_attention.append(
            TodayTimelineItemDTO(
                id=item.id,
                source_type=item.source_type,
                source_id=item.source_id,
                title=item.title,
                start=item_dt,
                end=item_dt,
                all_day=True,
                priority=item.priority,
                status=item.status or "ATTENTION",
                navigation_target=item.navigation_target,
                category_name=item.category_name,
                location=item.location,
                meta_info=item.meta_info
            )
        )

    return ApiSuccessResponse(
        data=TodayResponseDTO(
            date=today.isoformat(),
            timezone=tz_str,
            home_id=home_ctx.home_id,
            home_name=home.name if home else None,
            summary=summary,
            needs_attention=needs_attention,
            timeline=timeline,
            attention_alerts=legacy_attention,
            tasks=tasks_section,
            bills=bills_section,
            calendar=calendar_section,
            inventory=inventory_section,
            shopping=shopping_section,
            family=family_section,
            notifications=notifications_section
        )
    )

