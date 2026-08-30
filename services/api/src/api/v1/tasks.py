import math
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import redis.asyncio as redis

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.cache.redis_client import get_redis_client
from src.infrastructure.database.models import (
    BillCategoryModel,
    BillModel,
    HomeMemberModel,
    HomeModel,
    TaskCategoryModel,
    TaskModel,
    TaskTemplateModel,
    UserModel,
    UserProfileModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.task import (
    AssignTaskRequest,
    CompleteTaskRequest,
    CreateTaskCategoryRequest,
    CreateTaskRequest,
    MessageResponse,
    PaginatedTasksResponse,
    TaskCategoryDTO,
    TaskDTO,
    TaskSummaryDTO,
    UpdateTaskRequest
)

router = APIRouter(prefix="/homes/{home_id}/tasks", tags=["Tasks & Household Responsibilities"])


def calculate_next_due_date(base_time: datetime, recurrence_type: str, interval_days: Optional[int] = None) -> datetime:
    if recurrence_type == "DAILY":
        return base_time + timedelta(days=1)
    elif recurrence_type == "WEEKLY":
        return base_time + timedelta(weeks=1)
    elif recurrence_type == "MONTHLY":
        return base_time + timedelta(days=30)
    elif recurrence_type == "YEARLY":
        return base_time + timedelta(days=365)
    elif recurrence_type == "CUSTOM_DAYS":
        return base_time + timedelta(days=interval_days or 30)
    return base_time


def compute_time_flags(task: TaskModel):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    is_overdue = False
    is_due_today = False

    if task.due_date and task.status not in ("COMPLETED", "CANCELLED"):
        due = task.due_date
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if due < now:
            is_overdue = True
        elif today_start <= due < today_end:
            is_due_today = True

    return is_overdue, is_due_today


async def map_task_dto(task: TaskModel, db: AsyncSession) -> TaskDTO:
    is_overdue, is_due_today = compute_time_flags(task)

    assigned_name = None
    if task.assigned_to:
        prof = await db.get(UserProfileModel, task.assigned_to)
        if isinstance(prof, UserProfileModel) and isinstance(prof.display_name, str):
            assigned_name = prof.display_name

    created_name = None
    if task.created_by:
        prof = await db.get(UserProfileModel, task.created_by)
        if isinstance(prof, UserProfileModel) and isinstance(prof.display_name, str):
            created_name = prof.display_name

    completed_name = None
    if task.completed_by:
        prof = await db.get(UserProfileModel, task.completed_by)
        if isinstance(prof, UserProfileModel) and isinstance(prof.display_name, str):
            completed_name = prof.display_name

    cat_name = None
    if task.category_id:
        cat = await db.get(TaskCategoryModel, task.category_id)
        if isinstance(cat, TaskCategoryModel) and isinstance(cat.name, str):
            cat_name = cat.name

    # Resolve linked bill details if present
    bill_id = None
    bill_title = None
    bill_amount = None
    bill_currency = None
    bill_status = None
    bill_due_date = None
    if task.bill_id:
        bill = await db.get(BillModel, task.bill_id)
        if bill and not getattr(bill, "deleted_at", None):
            bill_id = bill.id
            bill_title = bill.title
            bill_amount = bill.expected_amount
            bill_currency = bill.currency
            bill_status = bill.status
            bill_due_date = bill.due_date

    return TaskDTO(
        id=task.id or uuid4(),
        home_id=task.home_id,
        template_id=task.template_id,
        category_id=task.category_id,
        category_name=cat_name,
        title=task.title,
        description=task.description,
        priority=task.priority or "NORMAL",
        status=task.status or "TODO",
        due_date=task.due_date,
        is_overdue=is_overdue,
        is_due_today=is_due_today,
        recurrence_type=task.recurrence_type or "NONE",
        recurrence_interval_days=task.recurrence_interval_days,
        recurrence_strategy=task.recurrence_strategy or "SCHEDULED_DATE",
        parent_recurring_task_id=task.parent_recurring_task_id,
        assigned_to=task.assigned_to,
        assigned_to_name=assigned_name,
        bill_id=bill_id,
        bill_title=bill_title,
        bill_amount=bill_amount,
        bill_currency=bill_currency,
        bill_status=bill_status,
        bill_due_date=bill_due_date,
        created_by=task.created_by or uuid4(),
        created_by_name=created_name,
        completed_by=task.completed_by,
        completed_by_name=completed_name,
        completed_at=task.completed_at,
        version=task.version or 1,
        created_at=task.created_at or datetime.now(timezone.utc),
        updated_at=task.updated_at or datetime.now(timezone.utc)
    )


@router.get("/summary", response_model=ApiSuccessResponse[TaskSummaryDTO])
async def get_tasks_summary(
    home_ctx: HomeContext = Depends(require_home_permission("tasks:view")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    active_filter = and_(
        TaskModel.home_id == home_ctx.home_id,
        TaskModel.deleted_at == None,
        TaskModel.status.in_(["TODO", "IN_PROGRESS"])
    )

    # 1. Total Active
    q_active = select(func.count()).select_from(TaskModel).where(active_filter)
    total_active = (await db.execute(q_active)).scalar() or 0

    # 2. Due Today
    q_today = select(func.count()).select_from(TaskModel).where(
        active_filter,
        TaskModel.due_date >= today_start,
        TaskModel.due_date < today_end
    )
    due_today = (await db.execute(q_today)).scalar() or 0

    # 3. Overdue
    q_overdue = select(func.count()).select_from(TaskModel).where(
        active_filter,
        TaskModel.due_date < now
    )
    overdue = (await db.execute(q_overdue)).scalar() or 0

    # 4. Upcoming
    q_upcoming = select(func.count()).select_from(TaskModel).where(
        active_filter,
        TaskModel.due_date >= today_end
    )
    upcoming = (await db.execute(q_upcoming)).scalar() or 0

    # 5. My Tasks
    q_my = select(func.count()).select_from(TaskModel).where(
        active_filter,
        TaskModel.assigned_to == home_ctx.user.id
    )
    my_tasks = (await db.execute(q_my)).scalar() or 0

    # 6. Completed History
    q_comp = select(func.count()).select_from(TaskModel).where(
        TaskModel.home_id == home_ctx.home_id,
        TaskModel.status == "COMPLETED"
    )
    completed_history_count = (await db.execute(q_comp)).scalar() or 0

    return ApiSuccessResponse(
        data=TaskSummaryDTO(
            total_active=total_active,
            due_today=due_today,
            overdue=overdue,
            upcoming=upcoming,
            my_tasks=my_tasks,
            completed_history_count=completed_history_count
        )
    )


@router.get("", response_model=ApiSuccessResponse[PaginatedTasksResponse])
async def list_tasks(
    view: Optional[str] = Query("all", pattern="^(all|today|upcoming|overdue|my_tasks|completed)$"),
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(TODO|IN_PROGRESS|COMPLETED|CANCELLED)$"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned member"),
    priority: Optional[str] = Query(None, pattern="^(LOW|NORMAL|HIGH)$"),
    category_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None, description="Search title or description"),
    sort_by: str = Query("due_date", pattern="^(due_date|priority|created_at|title)$"),
    order: str = Query("asc", pattern="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    home_ctx: HomeContext = Depends(require_home_permission("tasks:view")),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)

    filters = [
        TaskModel.home_id == home_ctx.home_id,
        TaskModel.deleted_at == None
    ]

    # View-specific filtering
    if view == "completed":
        filters.append(TaskModel.status == "COMPLETED")
    elif view == "today":
        filters.append(TaskModel.status.in_(["TODO", "IN_PROGRESS"]))
        filters.append(TaskModel.due_date >= today_start)
        filters.append(TaskModel.due_date < today_end)
    elif view == "upcoming":
        filters.append(TaskModel.status.in_(["TODO", "IN_PROGRESS"]))
        filters.append(TaskModel.due_date >= today_end)
    elif view == "overdue":
        filters.append(TaskModel.status.in_(["TODO", "IN_PROGRESS"]))
        filters.append(TaskModel.due_date < now)
    elif view == "my_tasks":
        filters.append(TaskModel.status.in_(["TODO", "IN_PROGRESS"]))
        filters.append(TaskModel.assigned_to == home_ctx.user.id)
    else:  # all
        if status_filter:
            filters.append(TaskModel.status == status_filter)
        else:
            filters.append(TaskModel.status.in_(["TODO", "IN_PROGRESS"]))

    if assigned_to and view != "my_tasks":
        filters.append(TaskModel.assigned_to == assigned_to)

    if priority:
        filters.append(TaskModel.priority == priority)

    if category_id:
        filters.append(TaskModel.category_id == category_id)

    if search:
        search_clean = f"%{search.strip()}%"
        filters.append(
            or_(
                TaskModel.title.ilike(search_clean),
                TaskModel.description.ilike(search_clean)
            )
        )

    # Total count
    count_query = select(func.count()).select_from(TaskModel).where(*filters)
    total = (await db.execute(count_query)).scalar() or 0

    sort_col = getattr(TaskModel, sort_by)
    if order == "desc":
        sort_expr = sort_col.desc().nullslast()
    else:
        sort_expr = sort_col.asc().nullslast()

    query = (
        select(TaskModel)
        .where(*filters)
        .order_by(sort_expr, TaskModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )

    result = await db.execute(query)
    tasks = result.scalars().all()

    dtos = [await map_task_dto(t, db) for t in tasks]
    total_pages = math.ceil(total / page_size) if total > 0 else 1

    return ApiSuccessResponse(
        data=PaginatedTasksResponse(
            items=dtos,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.post("", response_model=ApiSuccessResponse[TaskDTO], status_code=status.HTTP_201_CREATED)
async def create_task(
    payload: CreateTaskRequest,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:create")),
    db: AsyncSession = Depends(get_db),
    redis_client: Optional[redis.Redis] = Depends(get_redis_client),
):
    # Assignment verification: If assigned, target user MUST be an active member of THIS home
    if payload.assigned_to:
        q_mem = select(HomeMemberModel).where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.user_id == payload.assigned_to,
            HomeMemberModel.status == "ACTIVE"
        )
        mem = (await db.execute(q_mem)).scalar_one_or_none()
        if not mem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not an active member of this home."
            )

    # Category verification: Category must belong to this home or auto-create by name
    resolved_category_id = None
    if payload.category_id:
        cat = await db.get(TaskCategoryModel, payload.category_id)
        if not cat or cat.home_id != home_ctx.home_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category for this home."
            )
        resolved_category_id = cat.id
    elif payload.category_name or payload.category:
        cat_clean = (payload.category_name or payload.category).strip()
        if cat_clean:
            existing_cat = (await db.execute(
                select(TaskCategoryModel).where(
                    TaskCategoryModel.home_id == home_ctx.home_id,
                    func.lower(TaskCategoryModel.name) == cat_clean.lower()
                )
            )).scalar_one_or_none()
            if existing_cat:
                resolved_category_id = existing_cat.id
            else:
                new_cat = TaskCategoryModel(
                    home_id=home_ctx.home_id,
                    name=cat_clean,
                    sort_order=0
                )
                db.add(new_cat)
                await db.flush()
                resolved_category_id = new_cat.id

    # Bill Integration: Associate with existing bill or create authoritative Bill record
    resolved_bill_id = None
    if payload.bill_id:
        bill = await db.get(BillModel, payload.bill_id)
        if bill and bill.home_id == home_ctx.home_id and not bill.deleted_at:
            resolved_bill_id = bill.id
    elif payload.bill_amount and payload.bill_amount > 0:
        home = (await db.execute(select(HomeModel).where(HomeModel.id == home_ctx.home_id))).scalar_one_or_none()
        curr = payload.bill_currency or (home.currency if home else "INR")
        bill_due = payload.bill_due_date or (payload.due_date.date() if payload.due_date else date.today())
        bill_rec = payload.bill_recurrence_type or payload.recurrence_type or "NONE"

        bill_cat_name = (payload.bill_category or payload.category_name or payload.category or "Utilities").strip()
        b_cat = (await db.execute(
            select(BillCategoryModel).where(
                BillCategoryModel.home_id == home_ctx.home_id,
                func.lower(BillCategoryModel.name) == bill_cat_name.lower()
            )
        )).scalar_one_or_none()
        b_cat_id = b_cat.id if b_cat else None
        if not b_cat_id and bill_cat_name:
            new_bcat = BillCategoryModel(
                home_id=home_ctx.home_id,
                name=bill_cat_name,
                sort_order=0
            )
            db.add(new_bcat)
            await db.flush()
            b_cat_id = new_bcat.id

        new_bill = BillModel(
            home_id=home_ctx.home_id,
            category_id=b_cat_id,
            title=payload.title,
            expected_amount=payload.bill_amount,
            currency=curr,
            due_date=bill_due,
            recurrence_type=bill_rec,
            recurrence_interval_days=payload.recurrence_interval_days,
            recurrence_strategy=payload.recurrence_strategy or "SCHEDULED_DATE",
            status="UNPAID",
            amount_paid=Decimal("0.00"),
            responsible_member_id=payload.assigned_to,
            notes=payload.bill_notes or f"Created via Task: {payload.title}",
            version=1,
            created_by=home_ctx.user.id
        )
        db.add(new_bill)
        await db.flush()
        resolved_bill_id = new_bill.id

    task = TaskModel(
        home_id=home_ctx.home_id,
        template_id=payload.template_id,
        category_id=resolved_category_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority or "NORMAL",
        status="TODO",
        due_date=payload.due_date,
        recurrence_type=payload.recurrence_type or "NONE",
        recurrence_interval_days=payload.recurrence_interval_days,
        recurrence_strategy=payload.recurrence_strategy or "SCHEDULED_DATE",
        assigned_to=payload.assigned_to,
        bill_id=resolved_bill_id,
        created_by=home_ctx.user.id,
        version=1
    )
    db.add(task)
    if payload.assigned_to:
        from src.infrastructure.database.models import NotificationModel
        notif = NotificationModel(
            home_id=home_ctx.home_id,
            user_id=payload.assigned_to,
            title="Task Assigned",
            body=f"You have been assigned to task: {task.title}",
            type="TASK_ASSIGNED"
        )
        db.add(notif)
    await db.commit()
    await db.refresh(task)

    dto = await map_task_dto(task, db)
    return ApiSuccessResponse(data=dto)


@router.get("/{task_id}", response_model=ApiSuccessResponse[TaskDTO])
async def get_task(
    task_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:view")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task or task.home_id != home_ctx.home_id or task.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this home."
        )

    dto = await map_task_dto(task, db)
    return ApiSuccessResponse(data=dto)


@router.patch("/{task_id}", response_model=ApiSuccessResponse[TaskDTO])
async def update_task(
    task_id: UUID,
    payload: UpdateTaskRequest,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:edit")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task or task.home_id != home_ctx.home_id or task.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this home."
        )

    # Optimistic concurrency check
    if payload.version is not None and payload.version != task.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task has been modified by another household member. Please refresh."
        )

    # Validate assignee if updated
    if payload.assigned_to is not None:
        q_mem = select(HomeMemberModel).where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.user_id == payload.assigned_to,
            HomeMemberModel.status == "ACTIVE"
        )
        mem = (await db.execute(q_mem)).scalar_one_or_none()
        if not mem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not an active member of this home."
            )
        task.assigned_to = payload.assigned_to

    if payload.title is not None:
        task.title = payload.title
    if payload.description is not None:
        task.description = payload.description
    if payload.priority is not None:
        task.priority = payload.priority
    if payload.status is not None:
        task.status = payload.status
    if payload.category_id is not None:
        cat = await db.get(TaskCategoryModel, payload.category_id)
        if not cat or cat.home_id != home_ctx.home_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category for this home."
            )
        task.category_id = payload.category_id
    elif payload.category_name or payload.category:
        cat_clean = (payload.category_name or payload.category).strip()
        if cat_clean:
            existing_cat = (await db.execute(
                select(TaskCategoryModel).where(
                    TaskCategoryModel.home_id == home_ctx.home_id,
                    func.lower(TaskCategoryModel.name) == cat_clean.lower()
                )
            )).scalar_one_or_none()
            if existing_cat:
                task.category_id = existing_cat.id
            else:
                new_cat = TaskCategoryModel(
                    home_id=home_ctx.home_id,
                    name=cat_clean,
                    sort_order=0
                )
                db.add(new_cat)
                await db.flush()
                task.category_id = new_cat.id

    if payload.bill_id is not None:
        if payload.bill_id:
            bill = await db.get(BillModel, payload.bill_id)
            if bill and bill.home_id == home_ctx.home_id:
                task.bill_id = bill.id
        else:
            task.bill_id = None

    if payload.due_date is not None:
        task.due_date = payload.due_date
    if payload.recurrence_type is not None:
        task.recurrence_type = payload.recurrence_type
    if payload.recurrence_interval_days is not None:
        task.recurrence_interval_days = payload.recurrence_interval_days
    if payload.recurrence_strategy is not None:
        task.recurrence_strategy = payload.recurrence_strategy

    task.version += 1
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    dto = await map_task_dto(task, db)
    return ApiSuccessResponse(data=dto)


@router.post("/{task_id}/complete", response_model=ApiSuccessResponse[TaskDTO])
async def complete_task(
    task_id: UUID,
    payload: Optional[CompleteTaskRequest] = None,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:complete")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not isinstance(task, TaskModel):
        q = select(TaskModel).where(TaskModel.id == task_id, TaskModel.home_id == home_ctx.home_id, TaskModel.deleted_at.is_(None))
        task = (await db.execute(q)).scalar_one_or_none()
    if not task or task.home_id != home_ctx.home_id or task.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this home."
        )

    if task.status == "COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Task is already completed."
        )
    if task.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot complete a cancelled task."
        )

    # Optimistic concurrency check
    if payload and payload.version is not None and payload.version != task.version:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Task has been modified by another household member. Please refresh."
        )

    now = datetime.now(timezone.utc)
    task.status = "COMPLETED"
    task.completed_by = home_ctx.user.id
    task.completed_at = now
    task.version = (task.version or 1) + 1
    task.updated_at = now

    # Recurrence Engine Execution
    if task.recurrence_type and task.recurrence_type != "NONE":
        base_time = task.due_date if (task.recurrence_strategy == "SCHEDULED_DATE" and task.due_date) else now
        if base_time.tzinfo is None:
            base_time = base_time.replace(tzinfo=timezone.utc)

        if task.recurrence_type == "DAILY":
            next_due = base_time + timedelta(days=1)
        elif task.recurrence_type == "WEEKLY":
            next_due = base_time + timedelta(days=7)
        elif task.recurrence_type == "MONTHLY":
            next_due = base_time + timedelta(days=30)
        elif task.recurrence_type == "YEARLY":
            next_due = base_time + timedelta(days=365)
        elif task.recurrence_type == "CUSTOM_DAYS":
            interval = task.recurrence_interval_days or 30
            next_due = base_time + timedelta(days=interval)
        else:
            next_due = base_time + timedelta(days=7)

        next_task = TaskModel(
            home_id=task.home_id,
            template_id=task.template_id,
            category_id=task.category_id,
            title=task.title,
            description=task.description,
            priority=task.priority,
            status="TODO",
            due_date=next_due,
            recurrence_type=task.recurrence_type,
            recurrence_interval_days=task.recurrence_interval_days,
            recurrence_strategy=task.recurrence_strategy,
            parent_recurring_task_id=task.parent_recurring_task_id or task.id,
            assigned_to=task.assigned_to,
            created_by=home_ctx.user.id,
            version=1
        )
        db.add(next_task)

    await db.commit()
    await db.refresh(task)

    dto = await map_task_dto(task, db)
    return ApiSuccessResponse(data=dto)


@router.post("/{task_id}/assign", response_model=ApiSuccessResponse[TaskDTO])
async def assign_task(
    task_id: UUID,
    payload: AssignTaskRequest,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:edit")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task or task.home_id != home_ctx.home_id or task.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this home."
        )

    if payload.assigned_to is not None:
        q_mem = select(HomeMemberModel).where(
            HomeMemberModel.home_id == home_ctx.home_id,
            HomeMemberModel.user_id == payload.assigned_to,
            HomeMemberModel.status == "ACTIVE"
        )
        mem = (await db.execute(q_mem)).scalar_one_or_none()
        if not mem:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assigned user is not an active member of this home."
            )
        task.assigned_to = payload.assigned_to
    else:
        task.assigned_to = None

    task.version += 1
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    dto = await map_task_dto(task, db)
    return ApiSuccessResponse(data=dto)


@router.post("/{task_id}/reopen", response_model=ApiSuccessResponse[TaskDTO])
async def reopen_task(
    task_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:edit")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not isinstance(task, TaskModel):
        q = select(TaskModel).where(TaskModel.id == task_id, TaskModel.home_id == home_ctx.home_id, TaskModel.deleted_at.is_(None))
        task = (await db.execute(q)).scalar_one_or_none()
    if not task or task.home_id != home_ctx.home_id or task.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this home."
        )

    task.status = "TODO"
    task.completed_at = None
    task.completed_by = None
    task.version = (task.version or 1) + 1
    task.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(task)

    dto = await map_task_dto(task, db)
    return ApiSuccessResponse(data=dto, message="Task reopened successfully.")


@router.delete("/{task_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_task(
    task_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:delete")),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(TaskModel, task_id)
    if not task or task.home_id != home_ctx.home_id or task.deleted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found in this home."
        )

    task.deleted_at = datetime.now(timezone.utc)
    task.status = "CANCELLED"
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Task successfully cancelled and removed."))


# -------------------------------------------------------------
# Home Task Categories
# -------------------------------------------------------------
@router.get("/categories", response_model=ApiSuccessResponse[List[TaskCategoryDTO]])
async def list_task_categories(
    home_ctx: HomeContext = Depends(require_home_permission("tasks:view")),
    db: AsyncSession = Depends(get_db),
):
    query = select(TaskCategoryModel).where(TaskCategoryModel.home_id == home_ctx.home_id).order_by(TaskCategoryModel.sort_order.asc(), TaskCategoryModel.name.asc())
    cats = (await db.execute(query)).scalars().all()
    dtos = [
        TaskCategoryDTO(
            id=c.id,
            home_id=c.home_id,
            name=c.name,
            icon=c.icon,
            color=c.color,
            sort_order=c.sort_order,
            created_at=c.created_at,
            updated_at=c.updated_at
        ) for c in cats
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("/categories", response_model=ApiSuccessResponse[TaskCategoryDTO], status_code=status.HTTP_201_CREATED)
async def create_task_category(
    payload: CreateTaskCategoryRequest,
    home_ctx: HomeContext = Depends(require_home_permission("tasks:create")),
    db: AsyncSession = Depends(get_db),
):
    cat = TaskCategoryModel(
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
        data=TaskCategoryDTO(
            id=cat.id,
            home_id=cat.home_id,
            name=cat.name,
            icon=cat.icon,
            color=cat.color,
            sort_order=cat.sort_order,
            created_at=cat.created_at,
            updated_at=cat.updated_at
        )
    )
