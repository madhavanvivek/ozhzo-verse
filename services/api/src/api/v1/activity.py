from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query, status
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
    InventoryItemModel,
    LocationMovementModel,
    PurchaseItemModel,
    StockMovementModel,
    TaskModel,
    UserModel
)
from src.schemas.activity import (
    HomeActivityItemDTO,
    HomeActivityResponseDTO
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/homes/{home_id}/activity", tags=["Home Activity"])


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
    elif seconds < 604800:
        days = seconds // 86400
        return f"{days}d ago"
    else:
        return dt.strftime("%d %b %Y")


@router.get("", response_model=ApiSuccessResponse[HomeActivityResponseDTO])
async def get_home_activity_feed(
    limit: int = Query(20, ge=1, le=50),
    home_ctx: HomeContext = Depends(require_home_permission("homes:view")),
    db: AsyncSession = Depends(get_db),
):
    activities: List[HomeActivityItemDTO] = []

    # 1. Stock Movements
    stock_q = (
        select(StockMovementModel)
        .options(selectinload(StockMovementModel.item), selectinload(StockMovementModel.user))
        .where(StockMovementModel.home_id == home_ctx.home_id)
        .order_by(StockMovementModel.created_at.desc())
        .limit(limit)
    )
    stock_moves = (await db.execute(stock_q)).scalars().all()
    for s in stock_moves:
        item_name = s.item.name if s.item else "Supplies"
        actor_name = s.user.profile.display_name if (s.user and s.user.profile) else "Home Member"
        action_verb = "added" if s.movement_type == "RESTOCK" else "consumed" if s.movement_type == "CONSUMPTION" else "adjusted"
        activities.append(
            HomeActivityItemDTO(
                id=s.id,
                activity_type="STOCK_MOVE",
                title=f"{item_name} Stock Update",
                description=f"{actor_name} {action_verb} {abs(s.quantity)} {s.item.unit if s.item else ''}",
                actor_id=s.user_id,
                actor_name=actor_name,
                timestamp=s.created_at,
                time_ago=format_time_ago(s.created_at),
                navigation_target=f"/inventory/{s.item_id}"
            )
        )

    # 2. Location Movements
    loc_q = (
        select(LocationMovementModel)
        .options(
            selectinload(LocationMovementModel.item),
            selectinload(LocationMovementModel.from_location),
            selectinload(LocationMovementModel.to_location),
            selectinload(LocationMovementModel.user)
        )
        .where(LocationMovementModel.home_id == home_ctx.home_id)
        .order_by(LocationMovementModel.created_at.desc())
        .limit(limit)
    )
    loc_moves = (await db.execute(loc_q)).scalars().all()
    for l in loc_moves:
        item_name = l.item.name if l.item else "Item"
        actor_name = l.user.profile.display_name if (l.user and l.user.profile) else "Home Member"
        from_name = l.from_location.name if l.from_location else "Previous Location"
        to_name = l.to_location.name if l.to_location else "New Location"
        activities.append(
            HomeActivityItemDTO(
                id=l.id,
                activity_type="LOCATION_MOVE",
                title=f"{item_name} Relocated",
                description=f"{actor_name} moved {item_name} from {from_name} to {to_name}",
                actor_id=l.user_id,
                actor_name=actor_name,
                timestamp=l.created_at,
                time_ago=format_time_ago(l.created_at),
                navigation_target=f"/inventory/{l.item_id}"
            )
        )

    # 3. Completed Tasks
    tasks_q = (
        select(TaskModel)
        .options(selectinload(TaskModel.assignee))
        .where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.status == "COMPLETED",
            TaskModel.completed_at.is_not(None)
        )
        .order_by(TaskModel.completed_at.desc())
        .limit(limit)
    )
    completed_tasks = (await db.execute(tasks_q)).scalars().all()
    for t in completed_tasks:
        actor_name = t.assignee.profile.display_name if (t.assignee and t.assignee.profile) else "Home Member"
        ts = t.completed_at or t.updated_at
        activities.append(
            HomeActivityItemDTO(
                id=t.id,
                activity_type="TASK_COMPLETED",
                title=f"Task Completed",
                description=f'{actor_name} completed "{t.title}"',
                actor_id=t.assigned_to,
                actor_name=actor_name,
                timestamp=ts,
                time_ago=format_time_ago(ts),
                navigation_target=f"/tasks/{t.id}"
            )
        )

    # 4. Bill Payments
    payments_q = (
        select(BillPaymentModel)
        .options(selectinload(BillPaymentModel.bill), selectinload(BillPaymentModel.payer))
        .where(BillPaymentModel.home_id == home_ctx.home_id)
        .order_by(BillPaymentModel.created_at.desc())
        .limit(limit)
    )
    bill_payments = (await db.execute(payments_q)).scalars().all()
    for bp in bill_payments:
        bill_title = bp.bill.title if bp.bill else "Bill"
        actor_name = bp.payer.profile.display_name if (bp.payer and bp.payer.profile) else "Home Member"
        activities.append(
            HomeActivityItemDTO(
                id=bp.id,
                activity_type="BILL_PAID",
                title=f"Payment Recorded",
                description=f'{actor_name} recorded payment of {bp.currency} {bp.amount_paid:.2f} for "{bill_title}"',
                actor_id=bp.paid_by,
                actor_name=actor_name,
                timestamp=bp.created_at,
                time_ago=format_time_ago(bp.created_at),
                navigation_target=f"/bills/{bp.bill_id}"
            )
        )

    # 5. Asset Loans
    loans_q = (
        select(AssetLoanModel)
        .options(selectinload(AssetLoanModel.asset))
        .where(AssetLoanModel.home_id == home_ctx.home_id)
        .order_by(AssetLoanModel.created_at.desc())
        .limit(limit)
    )
    loans = (await db.execute(loans_q)).scalars().all()
    for l in loans:
        asset_name = l.asset.name if l.asset else "Asset"
        activities.append(
            HomeActivityItemDTO(
                id=l.id,
                activity_type="ASSET_LOANED",
                title=f"Asset Borrowed",
                description=f"{l.borrower_name} borrowed {asset_name} (Expected return: {l.expected_return_date})",
                actor_id=l.borrower_user_id,
                actor_name=l.borrower_name,
                timestamp=l.created_at,
                time_ago=format_time_ago(l.created_at),
                navigation_target=f"/inventory/assets/{l.asset_id}"
            )
        )

    # Sort all activities chronologically descending
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    sliced_activities = activities[:limit]

    return ApiSuccessResponse(
        data=HomeActivityResponseDTO(
            items=sliced_activities,
            total=len(sliced_activities)
        )
    )
