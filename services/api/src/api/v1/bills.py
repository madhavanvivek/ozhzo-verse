import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    BillModel,
    BillPaymentModel,
    BillCategoryModel,
    BillTemplateModel,
    HomeModel,
    HomeMemberModel,
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
    interval_days: Optional[int],
    payment_date: date,
    strategy: str
) -> date:
    anchor = payment_date if strategy == "PAYMENT_DATE" else current_due

    if recurrence_type == "MONTHLY":
        year = anchor.year + (1 if anchor.month == 12 else 0)
        month = 1 if anchor.month == 12 else anchor.month + 1
        day = min(anchor.day, 28)
        return date(year, month, day)
    elif recurrence_type == "QUARTERLY":
        m = anchor.month + 3
        year = anchor.year + ((m - 1) // 12)
        month = ((m - 1) % 12) + 1
        day = min(anchor.day, 28)
        return date(year, month, day)
    elif recurrence_type == "HALF_YEARLY":
        m = anchor.month + 6
        year = anchor.year + ((m - 1) // 12)
        month = ((m - 1) % 12) + 1
        day = min(anchor.day, 28)
        return date(year, month, day)
    elif recurrence_type == "YEARLY":
        return date(anchor.year + 1, anchor.month, min(anchor.day, 28))
    elif recurrence_type == "CUSTOM_DAYS":
        days = interval_days if interval_days and interval_days > 0 else 30
        return anchor + timedelta(days=days)
    else:
        return anchor


def map_bill_dto(
    bill: BillModel,
    user_map: dict[UUID, str],
    category_map: dict[UUID, str]
) -> BillDTO:
    today = date.today()
    is_overdue = (bill.due_date < today and bill.status in ("UNPAID", "PARTIALLY_PAID"))
    is_due_today = (bill.due_date == today and bill.status != "PAID")
    remaining_balance = max(Decimal("0.00"), bill.expected_amount - bill.amount_paid)

    return BillDTO(
        id=bill.id,
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
        recurrence_type=bill.recurrence_type,
        recurrence_interval_days=bill.recurrence_interval_days,
        recurrence_strategy=bill.recurrence_strategy,
        parent_recurring_bill_id=bill.parent_recurring_bill_id,
        status=bill.status,
        amount_paid=bill.amount_paid,
        remaining_balance=remaining_balance,
        responsible_member_id=bill.responsible_member_id,
        responsible_member_name=user_map.get(bill.responsible_member_id) if bill.responsible_member_id else None,
        notes=bill.notes,
        version=bill.version,
        created_by=bill.created_by,
        created_by_name=user_map.get(bill.created_by),
        created_at=bill.created_at,
        updated_at=bill.updated_at
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

    user_map = {}
    if user_ids:
        users = (await db.execute(
            select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(user_ids))
        )).all()
        for u in users:
            name = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Member"
            user_map[u.id] = name

    category_map = {}
    if category_ids:
        cats = (await db.execute(
            select(BillCategoryModel.id, BillCategoryModel.name)
            .where(BillCategoryModel.id.in_(category_ids))
        )).all()
        for c in cats:
            category_map[c.id] = c.name

    dtos = [map_bill_dto(b, user_map, category_map) for b in bills]

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
):
    # Verify responsible member if provided
    if payload.responsible_member_id:
        member = await db.execute(
            select(HomeMemberModel).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id == payload.responsible_member_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )
        if not member.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Responsible member must be an active member of this home."
            )

    # Get home currency if not specified
    currency = payload.currency
    if not currency:
        home = (await db.execute(select(HomeModel).where(HomeModel.id == home_ctx.home_id))).scalar_one_or_none()
        currency = home.currency if home else "INR"

    bill = BillModel(
        home_id=home_ctx.home_id,
        template_id=payload.template_id,
        category_id=payload.category_id,
        title=payload.title,
        expected_amount=payload.expected_amount,
        currency=currency,
        due_date=payload.due_date,
        recurrence_type=payload.recurrence_type or "NONE",
        recurrence_interval_days=payload.recurrence_interval_days,
        recurrence_strategy=payload.recurrence_strategy or "SCHEDULED_DATE",
        status="UNPAID",
        amount_paid=Decimal("0.00"),
        responsible_member_id=payload.responsible_member_id,
        notes=payload.notes,
        version=1,
        created_by=home_ctx.user.id
    )
    db.add(bill)
    await db.commit()
    await db.refresh(bill)

    user_map = {home_ctx.user.id: f"{home_ctx.user.first_name} {home_ctx.user.last_name}".strip()}
    if bill.responsible_member_id and bill.responsible_member_id != home_ctx.user.id:
        resp_user = (await db.execute(
            select(UserProfileModel).where(UserProfileModel.user_id == bill.responsible_member_id)
        )).scalar_one_or_none()
        if resp_user:
            user_map[bill.responsible_member_id] = f"{resp_user.first_name} {resp_user.last_name}".strip()

    category_map = {}
    if bill.category_id:
        cat = (await db.execute(
            select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id)
        )).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    return ApiSuccessResponse(
        data=map_bill_dto(bill, user_map, category_map),
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
        select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name)
        .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
        .where(UserModel.id.in_(user_ids))
    )).all()
    user_map = {u.id: f"{u.first_name or ''} {u.last_name or ''}".strip() or "Member" for u in users}

    category_map = {}
    if bill.category_id:
        cat = (await db.execute(
            select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id)
        )).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    base_dto = map_bill_dto(bill, user_map, category_map)

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
        member = await db.execute(
            select(HomeMemberModel).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id == payload.responsible_member_id,
                HomeMemberModel.status == "ACTIVE"
            )
        )
        if not member.scalar_one_or_none():
            raise HTTPException(
                status_code=400,
                detail="Responsible member must be an active member of this home."
            )
        bill.responsible_member_id = payload.responsible_member_id

    if payload.title is not None:
        bill.title = payload.title
    if payload.expected_amount is not None:
        bill.expected_amount = payload.expected_amount
    if payload.currency is not None:
        bill.currency = payload.currency
    if payload.due_date is not None:
        bill.due_date = payload.due_date
    if payload.recurrence_type is not None:
        bill.recurrence_type = payload.recurrence_type
    if payload.recurrence_interval_days is not None:
        bill.recurrence_interval_days = payload.recurrence_interval_days
    if payload.recurrence_strategy is not None:
        bill.recurrence_strategy = payload.recurrence_strategy
    if payload.category_id is not None:
        bill.category_id = payload.category_id
    if payload.status is not None:
        bill.status = payload.status
    if payload.notes is not None:
        bill.notes = payload.notes

    bill.version += 1
    await db.commit()
    await db.refresh(bill)

    user_map = {home_ctx.user.id: f"{home_ctx.user.first_name} {home_ctx.user.last_name}".strip()}
    category_map = {}
    if bill.category_id:
        cat = (await db.execute(select(BillCategoryModel).where(BillCategoryModel.id == bill.category_id))).scalar_one_or_none()
        if cat:
            category_map[cat.id] = cat.name

    return ApiSuccessResponse(
        data=map_bill_dto(bill, user_map, category_map),
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

    # Determine Payer
    paid_by_id = payload.paid_by or home_ctx.user.id
    if payload.paid_by:
        member = await db.execute(
            select(HomeMemberModel).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id == payload.paid_by,
                HomeMemberModel.status == "ACTIVE"
            )
        )
        if not member.scalar_one_or_none():
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
    bill.amount_paid += payload.amount_paid
    if bill.amount_paid >= bill.expected_amount:
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
            if not existing_next.scalar_one_or_none():
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

    bill.version += 1
    await db.commit()
    await db.refresh(bill)

    user_map = {home_ctx.user.id: f"{home_ctx.user.first_name} {home_ctx.user.last_name}".strip()}
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
            select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(user_ids))
        )).all()
        for u in users:
            user_map[u.id] = f"{u.first_name or ''} {u.last_name or ''}".strip() or "Member"

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
