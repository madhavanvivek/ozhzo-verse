from datetime import date, datetime, timedelta, timezone
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AssetLoanModel,
    BillModel,
    EventModel,
    HomeMemberModel,
    InvitationModel,
    InventoryItemModel,
    TaskModel
)
from src.schemas.attention import (
    AttentionCenterResponse,
    AttentionItemDTO,
    AttentionSummaryDTO
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/homes/{home_id}/attention", tags=["Attention Center"])


@router.get("", response_model=ApiSuccessResponse[AttentionCenterResponse])
async def get_home_attention_center(
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    now_utc = datetime.now(timezone.utc)
    items: List[AttentionItemDTO] = []

    # 1. CRITICAL: Overdue Bills
    overdue_bills_q = (
        select(BillModel)
        .where(
            BillModel.home_id == home_ctx.home_id,
            BillModel.deleted_at.is_(None),
            BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]),
            (BillModel.expected_amount - BillModel.amount_paid) > Decimal("0.00"),
            BillModel.due_date < today
        )
        .order_by(BillModel.due_date.asc())
    )
    overdue_bills = (await db.execute(overdue_bills_q)).scalars().all()
    for b in overdue_bills:
        days_overdue = (today - b.due_date).days
        rem_balance = max(0, b.expected_amount - b.amount_paid)
        items.append(
            AttentionItemDTO(
                id=b.id,
                severity="CRITICAL",
                category="BILL_OVERDUE",
                title=f"Overdue Bill: {b.title}",
                subtitle=f"{b.currency} {rem_balance:.2f} was due {days_overdue} day(s) ago",
                action_label="Record Payment",
                navigation_target=f"/bills/{b.id}",
                meta_info={"due_date": b.due_date.isoformat(), "amount": str(rem_balance)}
            )
        )

    # 2. CRITICAL: Overdue Tasks
    overdue_tasks_q = (
        select(TaskModel)
        .options(selectinload(TaskModel.assignee))
        .where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.deleted_at.is_(None),
            TaskModel.status.in_(["TODO", "IN_PROGRESS"]),
            TaskModel.due_date < today
        )
        .order_by(TaskModel.due_date.asc())
    )
    overdue_tasks = (await db.execute(overdue_tasks_q)).scalars().all()
    for t in overdue_tasks:
        days_overdue = (today - t.due_date).days
        assignee_str = f" • Assigned: {t.assignee.profile.display_name}" if t.assignee and t.assignee.profile else ""
        items.append(
            AttentionItemDTO(
                id=t.id,
                severity="CRITICAL",
                category="TASK_OVERDUE",
                title=f"Overdue Task: {t.title}",
                subtitle=f"Due {days_overdue} day(s) ago{assignee_str}",
                action_label="Complete Task",
                navigation_target=f"/tasks/{t.id}",
                meta_info={"priority": t.priority, "due_date": t.due_date.isoformat()}
            )
        )

    # 3. HIGH: Bills Due Today
    today_bills_q = (
        select(BillModel)
        .where(
            BillModel.home_id == home_ctx.home_id,
            BillModel.deleted_at.is_(None),
            BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]),
            (BillModel.expected_amount - BillModel.amount_paid) > Decimal("0.00"),
            BillModel.due_date == today
        )
    )
    today_bills = (await db.execute(today_bills_q)).scalars().all()
    for b in today_bills:
        rem_balance = max(0, b.expected_amount - b.amount_paid)
        items.append(
            AttentionItemDTO(
                id=b.id,
                severity="HIGH",
                category="BILL_DUE_TODAY",
                title=f"Bill Due Today: {b.title}",
                subtitle=f"{b.currency} {rem_balance:.2f} due today",
                action_label="Record Payment",
                navigation_target=f"/bills/{b.id}",
                meta_info={"due_date": b.due_date.isoformat(), "amount": str(rem_balance)}
            )
        )

    # 4. HIGH: Tasks Due Today
    today_tasks_q = (
        select(TaskModel)
        .where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.deleted_at.is_(None),
            TaskModel.status.in_(["TODO", "IN_PROGRESS"]),
            TaskModel.due_date == today
        )
    )
    today_tasks = (await db.execute(today_tasks_q)).scalars().all()
    for t in today_tasks:
        items.append(
            AttentionItemDTO(
                id=t.id,
                severity="HIGH",
                category="TASK_DUE_TODAY",
                title=f"Task Due Today: {t.title}",
                subtitle=f"Priority: {t.priority}",
                action_label="Complete Task",
                navigation_target=f"/tasks/{t.id}",
                meta_info={"priority": t.priority}
            )
        )

    # 5. HIGH: Out of Stock Supplies
    empty_stock_q = (
        select(InventoryItemModel)
        .where(
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at.is_(None),
            InventoryItemModel.item_type == "CONSUMABLE",
            InventoryItemModel.quantity <= 0
        )
    )
    empty_stock = (await db.execute(empty_stock_q)).scalars().all()
    for i in empty_stock:
        loc = f" in {i.location_path}" if i.location_path else ""
        items.append(
            AttentionItemDTO(
                id=i.id,
                severity="HIGH",
                category="STOCK_EMPTY",
                title=f"Out of Stock: {i.name}",
                subtitle=f"0 {i.unit} remaining{loc}",
                action_label="Add to Purchase List",
                navigation_target=f"/inventory/{i.id}",
                meta_info={"unit": i.unit}
            )
        )

    # 6. NORMAL: Low Stock Supplies
    low_stock_q = (
        select(InventoryItemModel)
        .where(
            InventoryItemModel.home_id == home_ctx.home_id,
            InventoryItemModel.deleted_at.is_(None),
            InventoryItemModel.item_type == "CONSUMABLE",
            InventoryItemModel.quantity > 0,
            InventoryItemModel.quantity <= InventoryItemModel.min_threshold
        )
    )
    low_stock = (await db.execute(low_stock_q)).scalars().all()
    for i in low_stock:
        items.append(
            AttentionItemDTO(
                id=i.id,
                severity="NORMAL",
                category="STOCK_LOW",
                title=f"Running Low: {i.name}",
                subtitle=f"{i.quantity} {i.unit} left (Threshold: {i.min_threshold})",
                action_label="Restock",
                navigation_target=f"/inventory/{i.id}",
                meta_info={"quantity": str(i.quantity), "min_threshold": str(i.min_threshold)}
            )
        )

    # 7. NORMAL: Overdue Asset Loans
    overdue_loans_q = (
        select(AssetLoanModel)
        .options(selectinload(AssetLoanModel.asset))
        .where(
            AssetLoanModel.home_id == home_ctx.home_id,
            AssetLoanModel.status == "ACTIVE",
            AssetLoanModel.expected_return_date < today
        )
    )
    overdue_loans = (await db.execute(overdue_loans_q)).scalars().all()
    for l in overdue_loans:
        asset_name = l.asset.name if l.asset else "Asset"
        items.append(
            AttentionItemDTO(
                id=l.id,
                severity="NORMAL",
                category="ASSET_OVERDUE",
                title=f"Overdue Asset: {asset_name}",
                subtitle=f"Borrowed by {l.borrower_name} • Expected back on {l.expected_return_date}",
                action_label="Return Asset",
                navigation_target=f"/inventory/assets/{l.asset_id}",
                meta_info={"borrower": l.borrower_name}
            )
        )

    # 8. INFO: Today's Events
    start_today = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc)
    end_today = datetime.combine(today, datetime.max.time(), tzinfo=timezone.utc)
    events_q = (
        select(EventModel)
        .where(
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None),
            EventModel.start_time <= end_today,
            EventModel.end_time >= start_today
        )
    )
    today_events = (await db.execute(events_q)).scalars().all()
    for e in today_events:
        loc = f" • Location: {e.location}" if e.location else ""
        items.append(
            AttentionItemDTO(
                id=e.id,
                severity="INFO",
                category="EVENT_TODAY",
                title=f"Event Today: {e.title}",
                subtitle=f"{e.start_time.strftime('%I:%M %p') if not e.is_all_day else 'All Day'}{loc}",
                action_label="View Event",
                navigation_target=f"/calendar/{e.id}",
                meta_info={"all_day": e.is_all_day}
            )
        )

    # 9. INFO: Pending Member Invitations
    invites_q = (
        select(InvitationModel)
        .where(
            InvitationModel.home_id == home_ctx.home_id,
            InvitationModel.status == "PENDING"
        )
    )
    invites = (await db.execute(invites_q)).scalars().all()
    for inv in invites:
        items.append(
            AttentionItemDTO(
                id=inv.id,
                severity="INFO",
                category="INVITATION_PENDING",
                title=f"Pending Invitation: {inv.email}",
                subtitle=f"Invited as {inv.role}",
                action_label="Manage Members",
                navigation_target="/settings/members",
                meta_info={"email": inv.email, "role": inv.role}
            )
        )

    # Calculate summary counts
    critical_c = sum(1 for i in items if i.severity == "CRITICAL")
    high_c = sum(1 for i in items if i.severity == "HIGH")
    normal_c = sum(1 for i in items if i.severity == "NORMAL")
    info_c = sum(1 for i in items if i.severity == "INFO")

    return ApiSuccessResponse(
        data=AttentionCenterResponse(
            summary=AttentionSummaryDTO(
                critical_count=critical_c,
                high_count=high_c,
                normal_count=normal_c,
                info_count=info_c,
                total_attention_items=len(items)
            ),
            items=items
        )
    )
