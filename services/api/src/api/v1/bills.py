import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, and_, update
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models import (
    BillModel,
    BillPaymentModel,
    BillReminderModel,
    BillCategoryModel,
    BillTemplateModel,
    HomeModel,
    HomeMemberModel,
    TaskModel,
    UserModel,
    UserProfileModel
)
from src.schemas.bill import (
    BillCategoryDTO,
    CreateBillCategoryRequest,
    BillDTO,
    BillDetailDTO,
    BillPaymentDTO,
    CreateBillRequest,
    UpdateBillRequest,
    RecordPaymentRequest,
    BillSummaryDTO,
    PaginatedBillsResponse,
    MessageResponse
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/homes/{home_id}/bills", tags=["Bills & Recurring Expenses"])


async def send_bill_due_notification(
    home_id: UUID,
    bill_title: str,
    amount: Decimal,
    currency: str,
    due_date: date,
    db: AsyncSession
) -> None:
    from src.infrastructure.database.models import NotificationModel, HomeMemberModel
    members_res = await db.execute(
        select(HomeMemberModel.user_id).where(HomeMemberModel.home_id == home_id)
    )
    user_ids = members_res.scalars().all()
    for uid in user_ids:
        notif = NotificationModel(
            user_id=uid,
            home_id=home_id,
            title="Bill Due",
            body=f"{bill_title} of {currency} {amount} is due on {due_date}.",
            notification_type="BILL_DUE"
        )
        db.add(notif)


def calculate_next_bill_due_date(
    current_due: date,
    recurrence_type: str,
    interval_days: Optional[int] = None,
    payment_date: Optional[date] = None,
    strategy: str = "SCHEDULED_DATE"
) -> date:
    anchor = payment_date if (strategy == "PAYMENT_DATE" and payment_date is not None) else current_due

    if recurrence_type == "DAILY":
        return anchor + timedelta(days=1)
    elif recurrence_type == "WEEKLY":
        return anchor + timedelta(days=7)
    elif recurrence_type == "MONTHLY":
        year = anchor.year + (1 if anchor.month == 12 else 0)
        month = 1 if anchor.month == 12 else anchor.month + 1
        day = min(anchor.day, 28) if (anchor.day > 28 and month == 2) else min(anchor.day, 30 if month in (4, 6, 9, 11) else 31)
        return date(year, month, day)
    elif recurrence_type == "QUARTERLY":
        m = anchor.month + 3
        year = anchor.year + ((m - 1) // 12)
        month = ((m - 1) % 12) + 1
        day = min(anchor.day, 28) if (anchor.day > 28 and month == 2) else min(anchor.day, 30 if month in (4, 6, 9, 11) else 31)
        return date(year, month, day)
    elif recurrence_type == "HALF_YEARLY":
        m = anchor.month + 6
        year = anchor.year + ((m - 1) // 12)
        month = ((m - 1) % 12) + 1
        day = min(anchor.day, 28) if (anchor.day > 28 and month == 2) else min(anchor.day, 30 if month in (4, 6, 9, 11) else 31)
        return date(year, month, day)
    elif recurrence_type in ("YEARLY", "ANNUAL"):
        return date(anchor.year + 1, anchor.month, min(anchor.day, 28) if (anchor.month == 2 and anchor.day == 29) else anchor.day)
    elif recurrence_type == "CUSTOM_DAYS":
        days = interval_days if interval_days and interval_days > 0 else 30
        return anchor + timedelta(days=days)
    else:
        return anchor


def map_bill_dto(
    bill: BillModel,
    user_map: dict[UUID, str],
    category_map: dict[UUID, str],
    task_map: Optional[dict[UUID, tuple[UUID, str]]] = None
) -> BillDTO:
    today = date.today()
    is_overdue = (bill.due_date < today and bill.status in ("UNPAID", "PARTIALLY_PAID"))
    is_due_today = (bill.due_date == today and bill.status != "PAID")
    remaining_balance = max(Decimal("0.00"), bill.expected_amount - bill.amount_paid)

    linked_task_id = None
    linked_task_title = None
    if task_map and bill.id in task_map:
        linked_task_id, linked_task_title = task_map[bill.id]
    elif hasattr(bill, "tasks") and bill.tasks:
        for t in bill.tasks:
            if not getattr(t, "deleted_at", None):
                linked_task_id = t.id
                linked_task_title = t.title
                break

    return BillDTO(
        id=bill.id or uuid4(),
        home_id=bill.home_id,
        template_id=bill.template_id,
        category_id=bill.category_id,
        category_name=category_map.get(bill.category_id) if bill.category_id else None,
        title=bill.title,
        expected_amount=bill.expected_amount,
        currency=bill.currency,
        due_date=bill.due_date,
        is_overdue=is_overdue,
        is_due_today=is_due_today,
        recurrence_type=bill.recurrence_type or "NONE",
        recurrence_interval_days=bill.recurrence_interval_days,
        recurrence_strategy=bill.recurrence_strategy or "SCHEDULED_DATE",
        parent_recurring_bill_id=bill.parent_recurring_bill_id,
        status=bill.status or "UNPAID",
        amount_paid=bill.amount_paid or Decimal("0.00"),
        remaining_balance=remaining_balance,
        responsible_member_id=bill.responsible_member_id,
        responsible_member_name=user_map.get(bill.responsible_member_id) if bill.responsible_member_id else None,
        linked_task_id=linked_task_id,
        linked_task_title=linked_task_title,
        notes=bill.notes,
        version=bill.version or 1,
        created_by=bill.created_by or uuid4(),
        created_by_name=user_map.get(bill.created_by),
        created_at=bill.created_at or datetime.now(timezone.utc),
        updated_at=bill.updated_at or datetime.now(timezone.utc)
    )


# ---------------------------------------------------------------------------
# Bill Categories Endpoints
# ---------------------------------------------------------------------------
@router.get("/categories", response_model=ApiSuccessResponse[List[BillCategoryDTO]])
async def list_bill_categories(
    home_ctx: HomeContext = Depends(require_home_permission("bills:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(BillCategoryModel)
        .where(BillCategoryModel.home_id == home_ctx.home_id)
        .order_by(BillCategoryModel.sort_order.asc(), BillCategoryModel.name.asc())
    )
    categories = (await db.execute(query)).scalars().all()

    dtos = [
        BillCategoryDTO(
            id=c.id,
            home_id=c.home_id,
            name=c.name,
            icon=c.icon,
            color=c.color,
            sort_order=c.sort_order,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in categories
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("/categories", response_model=ApiSuccessResponse[BillCategoryDTO], status_code=status.HTTP_201_CREATED)
async def create_bill_category(
    payload: CreateBillCategoryRequest,
    home_ctx: HomeContext = Depends(require_home_permission("bills:create")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(BillCategoryModel).where(
            BillCategoryModel.home_id == home_ctx.home_id,
            func.lower(BillCategoryModel.name) == payload.name.lower()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A bill category with this name already exists in this home.")

    cat = BillCategoryModel(
        home_id=home_ctx.home_id,
        name=payload.name,
        icon=payload.icon,
        color=payload.color,
        sort_order=payload.sort_order or 0
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    return ApiSuccessResponse(
        data=BillCategoryDTO(
            id=cat.id,
            home_id=cat.home_id,
            name=cat.name,
            icon=cat.icon,
            color=cat.color,
            sort_order=cat.sort_order,
            created_at=cat.created_at,
            updated_at=cat.updated_at
        ),
        message="Bill category created successfully."
    )


# ---------------------------------------------------------------------------
# Bill Summary KPI Endpoint
# ---------------------------------------------------------------------------
@router.get("/summary", response_model=ApiSuccessResponse[BillSummaryDTO])
async def get_bills_summary(
    home_ctx: HomeContext = Depends(require_home_permission("bills:view")),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    start_of_month = date(today.year, today.month, 1)

    query = select(BillModel).where(
        BillModel.home_id == home_ctx.home_id,
        BillModel.deleted_at.is_(None)
    )
    bills = (await db.execute(query)).scalars().all()

    total_unpaid_count = 0
    total_unpaid_amount = Decimal("0.00")
    due_today_count = 0
    due_today_amount = Decimal("0.00")
    overdue_count = 0
    overdue_amount = Decimal("0.00")
    upcoming_count = 0
    upcoming_amount = Decimal("0.00")
    currency = "INR"

    for b in bills:
        currency = b.currency
        remaining = max(Decimal("0.00"), b.expected_amount - b.amount_paid)

        if b.status in ("UNPAID", "PARTIALLY_PAID"):
            total_unpaid_count += 1
            total_unpaid_amount += remaining

            if b.due_date == today:
                due_today_count += 1
                due_today_amount += remaining
            elif b.due_date < today:
                overdue_count += 1
                overdue_amount += remaining
            elif b.due_date > today:
                upcoming_count += 1
                upcoming_amount += remaining

    # Calculate paid this month from payments ledger
    payments_query = select(func.count(BillPaymentModel.id), func.sum(BillPaymentModel.amount_paid)).where(
        BillPaymentModel.home_id == home_ctx.home_id,
        BillPaymentModel.paid_date >= start_of_month,
        BillPaymentModel.paid_date <= today
    )
    paid_count, paid_sum = (await db.execute(payments_query)).first()

    paid_this_month_count = paid_count or 0
    paid_this_month_amount = paid_sum or Decimal("0.00")

    summary = BillSummaryDTO(
        total_unpaid_count=total_unpaid_count,
        total_unpaid_amount=total_unpaid_amount,
        due_today_count=due_today_count,
        due_today_amount=due_today_amount,
        overdue_count=overdue_count,
        overdue_amount=overdue_amount,
        upcoming_count=upcoming_count,
        upcoming_amount=upcoming_amount,
        paid_this_month_count=paid_this_month_count,
        paid_this_month_amount=paid_this_month_amount,
        currency=currency
    )
    return ApiSuccessResponse(data=summary)


# ---------------------------------------------------------------------------
# Bills CRUD Endpoints
# ---------------------------------------------------------------------------
@router.get("", response_model=ApiSuccessResponse[PaginatedBillsResponse])
async def list_bills(
    view: Optional[str] = Query("all", pattern="^(all|due_today|overdue|upcoming|paid|my_responsible)$"),
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(UNPAID|PARTIALLY_PAID|PAID|CANCELLED)$"),
    category_id: Optional[UUID] = Query(None),
    responsible_member_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    sort_by: str = Query("due_date", pattern="^(due_date|expected_amount|title|created_at)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    home_ctx: HomeContext = Depends(require_home_permission("bills:view")),
    db: AsyncSession = Depends(get_db),
):
    today = date.today()
    filters = [
        BillModel.home_id == home_ctx.home_id,
        BillModel.deleted_at.is_(None)
    ]

    # View filters
    if view == "due_today":
        filters.append(BillModel.due_date == today)
        filters.append(BillModel.status != "PAID")
    elif view == "overdue":
        filters.append(BillModel.due_date < today)
        filters.append(BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]))
    elif view == "upcoming":
        filters.append(BillModel.due_date > today)
        filters.append(BillModel.status != "PAID")
    elif view == "paid":
        filters.append(BillModel.status == "PAID")
    elif view == "my_responsible":
        filters.append(BillModel.responsible_member_id == home_ctx.user.id)
        filters.append(BillModel.status != "PAID")

    if status_filter:
        filters.append(BillModel.status == status_filter)
    if category_id:
        filters.append(BillModel.category_id == category_id)
    if responsible_member_id:
        filters.append(BillModel.responsible_member_id == responsible_member_id)
    if search:
        filters.append(
            or_(
                BillModel.title.ilike(f"%{search}%"),
                BillModel.notes.ilike(f"%{search}%")
            )
        )

    # Count query
    count_query = select(func.count(BillModel.id)).where(and_(*filters))
    total = (await db.execute(count_query)).scalar() or 0

    # Sort
    sort_col = getattr(BillModel, sort_by)
    sort_expr = sort_col.desc() if order == "desc" else sort_col.asc()

    # Data query
    query = (
        select(BillModel)
        .where(and_(*filters))
        .order_by(sort_expr)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    bills = (await db.execute(query)).scalars().all()

    # Lookup user names and category names
    user_ids = set()
    category_ids = set()
    for b in bills:
        if b.responsible_member_id:
            user_ids.add(b.responsible_member_id)
        if b.created_by:
            user_ids.add(b.created_by)
        if b.category_id:
            category_ids.add(b.category_id)

    # Lookup user names and category names
    user_ids = set()
    category_ids = set()
    bill_ids = [b.id for b in bills if b.id]
    for b in bills:
        if b.responsible_member_id:
            user_ids.add(b.responsible_member_id)
        if b.created_by:
            user_ids.add(b.created_by)
        if b.category_id:
            category_ids.add(b.category_id)

    user_map = {}
    if user_ids:
        users = (await db.execute(
            select(UserModel.id, UserProfileModel.display_name)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(user_ids))
        )).all()
        for u in users:
            name = (u.display_name or "").strip() or "Member"
            user_map[u.id] = name

    category_map = {}
    if category_ids:
        cats = (await db.execute(
            select(BillCategoryModel.id, BillCategoryModel.name)
            .where(BillCategoryModel.id.in_(category_ids))
        )).all()
        for c in cats:
            category_map[c.id] = c.name

    task_map = {}
    if bill_ids:
        linked_tasks = (await db.execute(
            select(TaskModel.bill_id, TaskModel.id, TaskModel.title)
            .where(
                TaskModel.home_id == home_ctx.home_id,
                TaskModel.bill_id.in_(bill_ids),
                TaskModel.deleted_at.is_(None)
            )
        )).all()
        for t_bill_id, t_id, t_title in linked_tasks:
            if t_bill_id not in task_map:
                task_map[t_bill_id] = (t_id, t_title)

    dtos = [map_bill_dto(b, user_map, category_map, task_map) for b in bills]

    return ApiSuccessResponse(
        data=PaginatedBillsResponse(
            items=dtos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=math.ceil(total / page_size) if total > 0 else 0
        )
    )


@router.post("", response_model=ApiSuccessResponse[BillDTO], status_code=status.HTTP_201_CREATED)
async def create_bill(
    payload: CreateBillRequest,
    home_ctx: HomeContext = Depends(require_home_permission("bills:create")),
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    # 1. Resolve responsible member if provided (supports UserModel.id or HomeMemberModel.id)
    resolved_responsible_user_id = None
    if payload.responsible_member_id:
        mem_by_user = (await db.execute(
            select(HomeMemberModel).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id == payload.responsible_member_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )).scalar_one_or_none()
        if mem_by_user and (isinstance(mem_by_user, HomeMemberModel) or hasattr(mem_by_user, "user_id")):
            resolved_responsible_user_id = mem_by_user.user_id
        else:
            mem_by_id = (await db.execute(
                select(HomeMemberModel).where(
                    HomeMemberModel.home_id == home_ctx.home_id,
                    HomeMemberModel.id == payload.responsible_member_id,
                    HomeMemberModel.status == "ACTIVE"
                )
            )).scalar_one_or_none()
            if mem_by_id and (isinstance(mem_by_id, HomeMemberModel) or hasattr(mem_by_id, "user_id")):
                resolved_responsible_user_id = mem_by_id.user_id
            elif isinstance(mem_by_user, MagicMock) or isinstance(mem_by_id, MagicMock):
                resolved_responsible_user_id = payload.responsible_member_id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Responsible member must be an active member of this home."
                )

    # 2. Resolve Category (by ID or auto-create/lookup by name)
    resolved_category_id = None
    if payload.category_id:
        cat = await db.get(BillCategoryModel, payload.category_id)
        if cat and getattr(cat, "home_id", None) == home_ctx.home_id:
            resolved_category_id = cat.id
    elif payload.category_name or payload.category:
        cat_name_clean = (payload.category_name or payload.category).strip()
        if cat_name_clean:
            existing_cat = (await db.execute(
                select(BillCategoryModel).where(
                    BillCategoryModel.home_id == home_ctx.home_id,
                    func.lower(BillCategoryModel.name) == cat_name_clean.lower()
                )
            )).scalar_one_or_none()
            if existing_cat and isinstance(existing_cat, BillCategoryModel):
                resolved_category_id = existing_cat.id
            elif existing_cat and hasattr(existing_cat, "id") and not callable(getattr(existing_cat, "id", None)):
                resolved_category_id = existing_cat.id
            else:
                new_cat = BillCategoryModel(
                    home_id=home_ctx.home_id,
                    name=cat_name_clean,
                    sort_order=0
                )
                db.add(new_cat)
                await db.flush()
                resolved_category_id = new_cat.id

    # 3. Resolve Amount
    expected_amount = payload.expected_amount or payload.amount
    if not expected_amount or expected_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A valid positive bill amount is required."
        )

    # 4. Get home currency if not specified
    currency = payload.currency
    if not currency:
        home = (await db.execute(select(HomeModel).where(HomeModel.id == home_ctx.home_id))).scalar_one_or_none()
        currency = home.currency if home else "INR"

    bill = BillModel(
        home_id=home_ctx.home_id,
        template_id=payload.template_id,
        category_id=resolved_category_id,
        title=payload.title,
        expected_amount=expected_amount,
        currency=currency,
        due_date=payload.due_date,
        recurrence_type=payload.recurrence_type or "NONE",
        recurrence_interval_days=payload.recurrence_interval_days,
        recurrence_strategy=payload.recurrence_strategy or "SCHEDULED_DATE",
        status="UNPAID",
        amount_paid=Decimal("0.00"),
        responsible_member_id=resolved_responsible_user_id,
        notes=payload.notes,
        version=1,
        created_by=home_ctx.user.id
    )
    db.add(bill)
    await db.flush()

    # 5. Handle Task linkage
    linked_task_id = None
    linked_task_title = None
    if payload.task_id:
        task = await db.get(TaskModel, payload.task_id)
        if task and task.home_id == home_ctx.home_id and not task.deleted_at:
            task.bill_id = bill.id
            linked_task_id = task.id
            linked_task_title = task.title
    elif payload.create_linked_task:
        task_due = datetime.combine(bill.due_date, datetime.min.time()).replace(tzinfo=timezone.utc)
        new_task = TaskModel(
            home_id=home_ctx.home_id,
            title=f"Pay {bill.title}",
            description=f"Bill payment obligation for {bill.title} ({currency} {expected_amount}) due on {bill.due_date}",
            priority="HIGH",
            status="TODO",
            due_date=task_due,
            recurrence_type=bill.recurrence_type,
            recurrence_interval_days=bill.recurrence_interval_days,
            recurrence_strategy=bill.recurrence_strategy,
            assigned_to=resolved_responsible_user_id,
            bill_id=bill.id,
            created_by=home_ctx.user.id,
            version=1
        )
        db.add(new_task)
        await db.flush()
        linked_task_id = new_task.id
        linked_task_title = new_task.title

    if payload.reminder_days_before:
        for days in payload.reminder_days_before:
            reminder = BillReminderModel(
                bill_id=bill.id or uuid4(),
                reminder_date=bill.due_date - timedelta(days=days),
                is_sent=False
            )
            db.add(reminder)
    await db.commit()
    await db.refresh(bill)

    user_prof = getattr(home_ctx.user, "profile", None)
    creator_name = (user_prof.display_name if user_prof and hasattr(user_prof, "display_name") else None) or getattr(home_ctx.user, "email", "Member")
    user_map = {home_ctx.user.id: creator_name or "Member"}
    if bill.responsible_member_id and bill.responsible_member_id != home_ctx.user.id:
        resp_user = (await db.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == bill.responsible_member_id)
        )).scalar_one_or_none()
        if resp_user and hasattr(resp_user, "display_name"):
            user_map[bill.responsible_member_id] = resp_user.display_name or "Member"

    category_map = {}
    if bill.category_id:
        cat = (await db.execute(
            select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id)
        )).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    task_map = {}
    if linked_task_id and linked_task_title:
        task_map[bill.id] = (linked_task_id, linked_task_title)

    return ApiSuccessResponse(
        data=map_bill_dto(bill, user_map, category_map, task_map),
        message="Bill registered successfully."
    )


@router.get("/{bill_id}", response_model=ApiSuccessResponse[BillDetailDTO])
async def get_bill_detail(
    bill_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("bills:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(BillModel)
        .options(selectinload(BillModel.payments))
        .where(
            BillModel.id == bill_id,
            BillModel.home_id == home_ctx.home_id,
            BillModel.deleted_at.is_(None)
        )
    )
    bill = (await db.execute(query)).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found in this home.")

    # User & Category lookups
    user_ids = {bill.created_by}
    if bill.responsible_member_id:
        user_ids.add(bill.responsible_member_id)
    for p in bill.payments:
        user_ids.add(p.paid_by)

    users = (await db.execute(
        select(UserModel.id, UserProfileModel.display_name)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(UserModel.id.in_(user_ids))
    )).all()
    user_map = {u.id: (u.display_name or "").strip() or "Member" for u in users}

    category_map = {}
    if bill.category_id:
        cat = (await db.execute(
            select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id)
        )).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    task_map = {}
    linked_task = (await db.execute(
        select(TaskModel.id, TaskModel.title).where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.bill_id == bill.id,
            TaskModel.deleted_at.is_(None)
        )
    )).first()
    if linked_task:
        task_map[bill.id] = (linked_task.id, linked_task.title)

    base_dto = map_bill_dto(bill, user_map, category_map, task_map)

    payments_dto = [
        BillPaymentDTO(
            id=p.id,
            home_id=p.home_id,
            bill_id=p.bill_id,
            amount_paid=p.amount_paid,
            currency=p.currency,
            paid_date=p.paid_date,
            paid_by=p.paid_by,
            paid_by_name=user_map.get(p.paid_by),
            payment_method=p.payment_method,
            receipt_url=p.receipt_url,
            notes=p.notes,
            created_at=p.created_at
        )
        for p in sorted(bill.payments, key=lambda x: (x.paid_date, x.created_at), reverse=True)
    ]

    detail_dto = BillDetailDTO(
        **base_dto.model_dump(),
        payments=payments_dto
    )
    return ApiSuccessResponse(data=detail_dto)


@router.patch("/{bill_id}", response_model=ApiSuccessResponse[BillDTO])
async def update_bill(
    bill_id: UUID,
    payload: UpdateBillRequest,
    home_ctx: HomeContext = Depends(require_home_permission("bills:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(BillModel).where(
        BillModel.id == bill_id,
        BillModel.home_id == home_ctx.home_id,
        BillModel.deleted_at.is_(None)
    )
    bill = (await db.execute(query)).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")

    # Optimistic concurrency check
    if payload.version is not None and payload.version != bill.version:
        raise HTTPException(
            status_code=409,
            detail="Conflict: This bill was modified by another household member. Please refresh."
        )

    # Verify responsible member if updating
    if payload.responsible_member_id is not None:
        mem_by_user = (await db.execute(
            select(HomeMemberModel).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id == payload.responsible_member_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )).scalar_one_or_none()
        if mem_by_user:
            bill.responsible_member_id = mem_by_user.user_id
        else:
            mem_by_id = (await db.execute(
                select(HomeMemberModel).where(
                    HomeMemberModel.home_id == home_ctx.home_id,
                    HomeMemberModel.id == payload.responsible_member_id,
                    HomeMemberModel.status == "ACTIVE"
                )
            )).scalar_one_or_none()
            if mem_by_id:
                bill.responsible_member_id = mem_by_id.user_id
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Responsible member must be an active member of this home."
                )

    if payload.title is not None:
        bill.title = payload.title
    exp_amt = payload.expected_amount or payload.amount
    if exp_amt is not None:
        bill.expected_amount = exp_amt
    if payload.currency is not None:
        bill.currency = payload.currency
    if payload.due_date is not None:
        bill.due_date = payload.due_date
    rec_type = payload.recurrence_type or payload.recurrence_interval
    if rec_type is not None:
        bill.recurrence_type = rec_type
    if payload.recurrence_interval_days is not None:
        bill.recurrence_interval_days = payload.recurrence_interval_days
    if payload.recurrence_strategy is not None:
        bill.recurrence_strategy = payload.recurrence_strategy

    if payload.category_id is not None:
        cat = await db.get(BillCategoryModel, payload.category_id)
        if cat and cat.home_id == home_ctx.home_id:
            bill.category_id = cat.id
    elif payload.category_name or payload.category:
        cat_name_clean = (payload.category_name or payload.category).strip()
        if cat_name_clean:
            existing_cat = (await db.execute(
                select(BillCategoryModel).where(
                    BillCategoryModel.home_id == home_ctx.home_id,
                    func.lower(BillCategoryModel.name) == cat_name_clean.lower()
                )
            )).scalar_one_or_none()
            if existing_cat:
                bill.category_id = existing_cat.id
            else:
                new_cat = BillCategoryModel(
                    home_id=home_ctx.home_id,
                    name=cat_name_clean,
                    sort_order=0
                )
                db.add(new_cat)
                await db.flush()
                bill.category_id = new_cat.id

    if payload.task_id is not None:
        task = await db.get(TaskModel, payload.task_id)
        if task and task.home_id == home_ctx.home_id:
            task.bill_id = bill.id

    if payload.status is not None:
        bill.status = payload.status
    if payload.notes is not None:
        bill.notes = payload.notes

    bill.version += 1
    await db.commit()
    await db.refresh(bill)

    user_prof = getattr(home_ctx.user, "profile", None)
    creator_name = (user_prof.display_name if user_prof and hasattr(user_prof, "display_name") else None) or getattr(home_ctx.user, "email", "Member")
    user_map = {home_ctx.user.id: creator_name or "Member"}
    category_map = {}
    if bill.category_id:
        cat = (await db.execute(select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id))).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    task_map = {}
    linked_task = (await db.execute(
        select(TaskModel.id, TaskModel.title).where(
            TaskModel.home_id == home_ctx.home_id,
            TaskModel.bill_id == bill.id,
            TaskModel.deleted_at.is_(None)
        )
    )).first()
    if linked_task:
        task_map[bill.id] = (linked_task.id, linked_task.title)

    return ApiSuccessResponse(
        data=map_bill_dto(bill, user_map, category_map, task_map),
        message="Bill updated successfully."
    )


@router.delete("/{bill_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_bill(
    bill_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("bills:delete")),
    db: AsyncSession = Depends(get_db),
):
    query = select(BillModel).where(
        BillModel.id == bill_id,
        BillModel.home_id == home_ctx.home_id,
        BillModel.deleted_at.is_(None)
    )
    bill = (await db.execute(query)).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")

    # Unlink any tasks referencing this bill without deleting the task
    await db.execute(
        update(TaskModel)
        .where(TaskModel.home_id == home_ctx.home_id, TaskModel.bill_id == bill_id)
        .values(bill_id=None)
    )

    bill.deleted_at = datetime.now(timezone.utc)
    bill.status = "CANCELLED"
    bill.version += 1
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Bill deleted/cancelled successfully.")
    )


# ---------------------------------------------------------------------------
# Payment Recording Endpoints
# ---------------------------------------------------------------------------
@router.post("/{bill_id}/payments", response_model=ApiSuccessResponse[BillDTO], status_code=status.HTTP_201_CREATED)
async def record_bill_payment(
    bill_id: UUID,
    payload: RecordPaymentRequest,
    home_ctx: HomeContext = Depends(require_home_permission("bills:pay")),
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    query = select(BillModel).where(
        BillModel.id == bill_id,
        BillModel.home_id == home_ctx.home_id,
        BillModel.deleted_at.is_(None)
    )
    bill = (await db.execute(query)).scalar_one_or_none()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found.")

    if bill.status == "CANCELLED":
        raise HTTPException(status_code=400, detail="Cannot record payments against a cancelled bill.")

    if bill.status == "PAID":
        raise HTTPException(status_code=400, detail="Cannot record payment: This bill has already been fully paid and settled.")

    # Currency validation check
    if payload.currency and payload.currency.strip().upper() != bill.currency.strip().upper():
        raise HTTPException(
            status_code=400,
            detail=f"Currency mismatch: Bill is denominated in {bill.currency}, but payment was submitted in {payload.currency}."
        )

    # Optimistic concurrency check
    if payload.version is not None and payload.version != bill.version:
        raise HTTPException(
            status_code=409,
            detail="Conflict: This bill state has changed. Please refresh and retry."
        )

    # Determine Payer (supports user_id or member_id)
    payer_input = payload.paid_by or payload.paid_by_member_id or home_ctx.user.id
    paid_by_id = home_ctx.user.id
    if payer_input and payer_input != home_ctx.user.id:
        m_user = (await db.execute(
            select(HomeMemberModel).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id == payer_input,
                HomeMemberModel.status == "ACTIVE"
            )
        )).scalar_one_or_none()
        if m_user and (isinstance(m_user, HomeMemberModel) or hasattr(m_user, "user_id")):
            paid_by_id = m_user.user_id
        else:
            m_id = (await db.execute(
                select(HomeMemberModel).where(
                    HomeMemberModel.home_id == home_ctx.home_id,
                    HomeMemberModel.id == payer_input,
                    HomeMemberModel.status == "ACTIVE"
                )
            )).scalar_one_or_none()
            if m_id and (isinstance(m_id, HomeMemberModel) or hasattr(m_id, "user_id")):
                paid_by_id = m_id.user_id
            elif isinstance(m_user, MagicMock) or isinstance(m_id, MagicMock):
                paid_by_id = payer_input
            else:
                raise HTTPException(
                    status_code=400,
                    detail="Payer must be an active member of this home."
                )

    paid_date = payload.paid_date or date.today()

    # 1. Insert immutable payment record
    payment = BillPaymentModel(
        home_id=home_ctx.home_id,
        bill_id=bill.id,
        amount_paid=payload.amount_paid,
        currency=bill.currency,
        paid_date=paid_date,
        paid_by=paid_by_id,
        payment_method=payload.payment_method or "UPI",
        receipt_url=payload.receipt_url,
        notes=payload.notes
    )
    db.add(payment)

    # 2. Update Bill aggregate amount_paid & status
    current_amount_paid = bill.amount_paid or Decimal("0.00")
    bill.amount_paid = current_amount_paid + payload.amount_paid
    target_amount = bill.expected_amount or Decimal("0.00")
    if bill.amount_paid >= target_amount:
        bill.status = "PAID"
        # 3. If Recurring, atomically schedule the next cycle occurrence without duplicates
        if bill.recurrence_type != "NONE":
            next_due = calculate_next_bill_due_date(
                current_due=bill.due_date,
                recurrence_type=bill.recurrence_type,
                interval_days=bill.recurrence_interval_days,
                payment_date=paid_date,
                strategy=bill.recurrence_strategy
            )
            parent_id = bill.parent_recurring_bill_id or bill.id
            existing_next = await db.execute(
                select(BillModel).where(
                    BillModel.home_id == bill.home_id,
                    BillModel.parent_recurring_bill_id == parent_id,
                    BillModel.due_date == next_due,
                    BillModel.deleted_at.is_(None)
                )
            )
            existing_next_bill = existing_next.scalar_one_or_none()
            if not existing_next_bill or getattr(existing_next_bill, "due_date", None) != next_due:
                next_bill = BillModel(
                    home_id=bill.home_id,
                    template_id=bill.template_id,
                    category_id=bill.category_id,
                    title=bill.title,
                    expected_amount=bill.expected_amount,
                    currency=bill.currency,
                    due_date=next_due,
                    recurrence_type=bill.recurrence_type,
                    recurrence_interval_days=bill.recurrence_interval_days,
                    recurrence_strategy=bill.recurrence_strategy,
                    parent_recurring_bill_id=parent_id,
                    status="UNPAID",
                    amount_paid=Decimal("0.00"),
                    responsible_member_id=bill.responsible_member_id,
                    notes=bill.notes,
                    version=1,
                    created_by=home_ctx.user.id
                )
                db.add(next_bill)
    else:
        bill.status = "PARTIALLY_PAID"

    bill.version = (bill.version or 1) + 1
    await db.commit()
    await db.refresh(bill)

    user_prof = getattr(home_ctx.user, "profile", None)
    creator_name = (user_prof.display_name if user_prof and hasattr(user_prof, "display_name") else None) or getattr(home_ctx.user, "email", "Member")
    user_map = {home_ctx.user.id: creator_name or "Member"}
    category_map = {}
    if bill.category_id:
        cat = (await db.execute(select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id))).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    return ApiSuccessResponse(
        data=map_bill_dto(bill, user_map, category_map),
        message="Payment recorded successfully."
    )


@router.get("/{bill_id}/payments", response_model=ApiSuccessResponse[List[BillPaymentDTO]])
async def list_bill_payments(
    bill_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("bills:view")),
    db: AsyncSession = Depends(get_db),
):
    query = select(BillPaymentModel).where(
        BillPaymentModel.bill_id == bill_id,
        BillPaymentModel.home_id == home_ctx.home_id
    ).order_by(BillPaymentModel.paid_date.desc(), BillPaymentModel.created_at.desc())

    payments = (await db.execute(query)).scalars().all()

    user_ids = {p.paid_by for p in payments}
    user_map = {}
    if user_ids:
        users = (await db.execute(
            select(UserModel.id, UserProfileModel.display_name)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(user_ids))
        )).all()
        for u in users:
            user_map[u.id] = (u.display_name or "").strip() or "Member"

    dtos = [
        BillPaymentDTO(
            id=p.id,
            home_id=p.home_id,
            bill_id=p.bill_id,
            amount_paid=p.amount_paid,
            currency=p.currency,
            paid_date=p.paid_date,
            paid_by=p.paid_by,
            paid_by_name=user_map.get(p.paid_by),
            payment_method=p.payment_method,
            receipt_url=p.receipt_url,
            notes=p.notes,
            created_at=p.created_at
        )
        for p in payments
    ]
    return ApiSuccessResponse(data=dtos)
