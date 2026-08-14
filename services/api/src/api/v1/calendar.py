import math
from datetime import date, datetime, time, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    EventCategoryModel,
    EventModel,
    EventParticipantModel,
    HomeMemberModel,
    HomeModel,
    TaskModel,
    BillModel,
    UserModel,
    UserProfileModel
)
from src.schemas.calendar import (
    CalendarProjectionResponse,
    CreateEventCategoryRequest,
    CreateEventRequest,
    EventCategoryDTO,
    EventDTO,
    EventParticipantDTO,
    MessageResponse,
    TimelineItemDTO,
    UpdateEventRequest,
    UpdateParticipantStatusRequest
)
from src.schemas.common import ApiSuccessResponse

router = APIRouter(prefix="/homes/{home_id}", tags=["Calendar & Household Events"])


def calculate_next_event_due_date(
    current_start: datetime,
    current_end: datetime,
    recurrence_type: str,
    interval_days: Optional[int] = None
) -> tuple[datetime, datetime]:
    duration = current_end - current_start
    if recurrence_type == "DAILY":
        next_start = current_start + timedelta(days=1)
    elif recurrence_type == "WEEKLY":
        next_start = current_start + timedelta(weeks=1)
    elif recurrence_type == "MONTHLY":
        # Advance 1 month
        month = current_start.month + 1
        year = current_start.year
        if month > 12:
            month = 1
            year += 1
        day = min(current_start.day, 28)
        next_start = current_start.replace(year=year, month=month, day=day)
    elif recurrence_type == "YEARLY":
        next_start = current_start.replace(year=current_start.year + 1)
    elif recurrence_type == "CUSTOM_DAYS" and interval_days and interval_days > 0:
        next_start = current_start + timedelta(days=interval_days)
    else:
        next_start = current_start + timedelta(days=7)
    return next_start, next_start + duration


# ---------------------------------------------------------------------------
# Category Endpoints
# ---------------------------------------------------------------------------
@router.get("/events/categories", response_model=ApiSuccessResponse[List[EventCategoryDTO]])
async def list_event_categories(
    home_ctx: HomeContext = Depends(require_home_permission("calendar:view")),
    db: AsyncSession = Depends(get_db),
):
    query = select(EventCategoryModel).where(
        EventCategoryModel.home_id == home_ctx.home_id
    ).order_by(EventCategoryModel.sort_order.asc(), EventCategoryModel.name.asc())
    cats = (await db.execute(query)).scalars().all()

    dtos = [
        EventCategoryDTO(
            id=c.id,
            home_id=c.home_id,
            name=c.name,
            icon=c.icon,
            color=c.color,
            sort_order=c.sort_order,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in cats
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("/events/categories", response_model=ApiSuccessResponse[EventCategoryDTO], status_code=status.HTTP_201_CREATED)
async def create_event_category(
    payload: CreateEventCategoryRequest,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:create")),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(
        select(EventCategoryModel).where(
            EventCategoryModel.home_id == home_ctx.home_id,
            func.lower(EventCategoryModel.name) == payload.name.strip().lower()
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail=f"An event category named '{payload.name}' already exists in this home."
        )

    cat = EventCategoryModel(
        home_id=home_ctx.home_id,
        name=payload.name.strip(),
        icon=payload.icon,
        color=payload.color,
        sort_order=payload.sort_order or 0
    )
    db.add(cat)
    await db.commit()
    await db.refresh(cat)

    return ApiSuccessResponse(
        data=EventCategoryDTO(
            id=cat.id,
            home_id=cat.home_id,
            name=cat.name,
            icon=cat.icon,
            color=cat.color,
            sort_order=cat.sort_order,
            created_at=cat.created_at,
            updated_at=cat.updated_at
        ),
        message="Event category created successfully."
    )


# ---------------------------------------------------------------------------
# Event CRUD Endpoints
# ---------------------------------------------------------------------------
@router.get("/events", response_model=ApiSuccessResponse[List[EventDTO]])
async def list_home_events(
    start_date: Optional[datetime] = Query(None, description="Start of date range (ISO format)"),
    end_date: Optional[datetime] = Query(None, description="End of date range (ISO format)"),
    category_id: Optional[UUID] = None,
    status: Optional[str] = None,
    participant_id: Optional[UUID] = None,
    search: Optional[str] = None,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:view")),
    db: AsyncSession = Depends(get_db),
):
    filters = [
        EventModel.home_id == home_ctx.home_id,
        EventModel.deleted_at.is_(None)
    ]

    if start_date:
        filters.append(EventModel.end_time >= start_date)
    if end_date:
        filters.append(EventModel.start_time <= end_date)
    if category_id:
        filters.append(EventModel.category_id == category_id)
    if status:
        filters.append(EventModel.status == status)
    if search:
        filters.append(EventModel.title.ilike(f"%{search.strip()}%"))

    query = (
        select(EventModel)
        .options(
            selectinload(EventModel.participants),
            selectinload(EventModel.category),
            selectinload(EventModel.creator)
        )
        .where(*filters)
        .order_by(EventModel.start_time.asc())
    )
    result = await db.execute(query)
    events = result.scalars().all()

    # Pre-fetch user profiles for participants and creators
    all_user_ids = {e.created_by for e in events}
    for e in events:
        for p in e.participants:
            all_user_ids.add(p.user_id)

    user_map = {}
    if all_user_ids:
        profiles_res = await db.execute(
            select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name, UserProfileModel.avatar_url)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(all_user_ids))
        )
        for row in profiles_res.all():
            full_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or "Member"
            user_map[row.id] = (full_name, row.avatar_url)

    event_dtos = []
    for e in events:
        part_dtos = []
        for p in e.participants:
            name, avatar = user_map.get(p.user_id, ("Member", None))
            part_dtos.append(
                EventParticipantDTO(
                    user_id=p.user_id,
                    display_name=name,
                    avatar_url=avatar,
                    status=p.status,
                    created_at=p.created_at
                )
            )

        if participant_id and not any(p.user_id == participant_id for p in e.participants):
            continue

        creator_name, _ = user_map.get(e.created_by, ("Member", None))
        event_dtos.append(
            EventDTO(
                id=e.id,
                home_id=e.home_id,
                category_id=e.category_id,
                category_name=e.category.name if e.category else None,
                title=e.title,
                description=e.description,
                location=e.location,
                start_time=e.start_time,
                end_time=e.end_time,
                is_all_day=e.is_all_day,
                recurrence_type=e.recurrence_type,
                recurrence_interval_days=e.recurrence_interval_days,
                parent_recurring_event_id=e.parent_recurring_event_id,
                status=e.status,
                reminder_minutes_before=e.reminder_minutes_before,
                version=e.version,
                created_by=e.created_by,
                created_by_name=creator_name,
                participants=part_dtos,
                created_at=e.created_at,
                updated_at=e.updated_at
            )
        )

    return ApiSuccessResponse(data=event_dtos)


@router.post("/events", response_model=ApiSuccessResponse[EventDTO], status_code=status.HTTP_201_CREATED)
async def create_event(
    payload: CreateEventRequest,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:create")),
    db: AsyncSession = Depends(get_db),
):
    # Validate participants belong to same Home
    if payload.participant_user_ids:
        active_members = (await db.execute(
            select(HomeMemberModel.user_id).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id.in_(payload.participant_user_ids),
                HomeMemberModel.status == "ACTIVE"
            )
        )).scalars().all()
        active_set = set(active_members)
        for uid in payload.participant_user_ids:
            if uid not in active_set:
                raise HTTPException(
                    status_code=400,
                    detail="All participants must be active members of this home."
                )

    # Validate category if provided
    if payload.category_id:
        cat = (await db.execute(
            select(EventCategoryModel).where(
                EventCategoryModel.id == payload.category_id,
                EventCategoryModel.home_id == home_ctx.home_id
            )
        )).scalar_one_or_none()
        if not cat:
            raise HTTPException(status_code=400, detail="Invalid event category.")

    event = EventModel(
        home_id=home_ctx.home_id,
        category_id=payload.category_id,
        title=payload.title,
        description=payload.description,
        location=payload.location,
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_all_day=payload.is_all_day,
        recurrence_type=payload.recurrence_type or "NONE",
        recurrence_interval_days=payload.recurrence_interval_days,
        status="CONFIRMED",
        reminder_minutes_before=payload.reminder_minutes_before,
        version=1,
        created_by=home_ctx.user.id
    )
    db.add(event)
    await db.flush()

    for uid in payload.participant_user_ids:
        db.add(EventParticipantModel(
            event_id=event.id,
            user_id=uid,
            status="INVITED"
        ))

    await db.commit()
    await db.refresh(event)

    # Pre-fetch participant profiles
    user_map = {home_ctx.user.id: (f"{home_ctx.user.first_name} {home_ctx.user.last_name}".strip(), None)}
    if payload.participant_user_ids:
        profiles_res = await db.execute(
            select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name, UserProfileModel.avatar_url)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(payload.participant_user_ids))
        )
        for row in profiles_res.all():
            full_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or "Member"
            user_map[row.id] = (full_name, row.avatar_url)

    part_dtos = []
    for uid in payload.participant_user_ids:
        name, avatar = user_map.get(uid, ("Member", None))
        part_dtos.append(
            EventParticipantDTO(
                user_id=uid,
                display_name=name,
                avatar_url=avatar,
                status="INVITED",
                created_at=datetime.now(timezone.utc)
            )
        )

    cat_name = None
    if event.category_id:
        cat = (await db.execute(select(EventCategoryModel).where(EventCategoryModel.id == event.category_id))).scalar_one_or_none()
        if cat:
            cat_name = cat.name

    dto = EventDTO(
        id=event.id,
        home_id=event.home_id,
        category_id=event.category_id,
        category_name=cat_name,
        title=event.title,
        description=event.description,
        location=event.location,
        start_time=event.start_time,
        end_time=event.end_time,
        is_all_day=event.is_all_day,
        recurrence_type=event.recurrence_type,
        recurrence_interval_days=event.recurrence_interval_days,
        parent_recurring_event_id=event.parent_recurring_event_id,
        status=event.status,
        reminder_minutes_before=event.reminder_minutes_before,
        version=event.version,
        created_by=event.created_by,
        created_by_name=f"{home_ctx.user.first_name} {home_ctx.user.last_name}".strip(),
        participants=part_dtos,
        created_at=event.created_at,
        updated_at=event.updated_at
    )
    return ApiSuccessResponse(data=dto, message="Event created successfully.")


@router.get("/events/{event_id}", response_model=ApiSuccessResponse[EventDTO])
async def get_event(
    event_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(EventModel)
        .options(
            selectinload(EventModel.participants),
            selectinload(EventModel.category),
            selectinload(EventModel.creator)
        )
        .where(
            EventModel.id == event_id,
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None)
        )
    )
    event = (await db.execute(query)).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    all_user_ids = {event.created_by} | {p.user_id for p in event.participants}
    user_map = {}
    if all_user_ids:
        profiles_res = await db.execute(
            select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name, UserProfileModel.avatar_url)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(all_user_ids))
        )
        for row in profiles_res.all():
            full_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or "Member"
            user_map[row.id] = (full_name, row.avatar_url)

    part_dtos = [
        EventParticipantDTO(
            user_id=p.user_id,
            display_name=user_map.get(p.user_id, ("Member", None))[0],
            avatar_url=user_map.get(p.user_id, ("Member", None))[1],
            status=p.status,
            created_at=p.created_at
        )
        for p in event.participants
    ]

    creator_name, _ = user_map.get(event.created_by, ("Member", None))

    return ApiSuccessResponse(
        data=EventDTO(
            id=event.id,
            home_id=event.home_id,
            category_id=event.category_id,
            category_name=event.category.name if event.category else None,
            title=event.title,
            description=event.description,
            location=event.location,
            start_time=event.start_time,
            end_time=event.end_time,
            is_all_day=event.is_all_day,
            recurrence_type=event.recurrence_type,
            recurrence_interval_days=event.recurrence_interval_days,
            parent_recurring_event_id=event.parent_recurring_event_id,
            status=event.status,
            reminder_minutes_before=event.reminder_minutes_before,
            version=event.version,
            created_by=event.created_by,
            created_by_name=creator_name,
            participants=part_dtos,
            created_at=event.created_at,
            updated_at=event.updated_at
        )
    )


@router.patch("/events/{event_id}", response_model=ApiSuccessResponse[EventDTO])
async def update_event(
    event_id: UUID,
    payload: UpdateEventRequest,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(EventModel)
        .options(selectinload(EventModel.participants))
        .where(
            EventModel.id == event_id,
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None)
        )
    )
    event = (await db.execute(query)).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    # Optimistic concurrency check
    if payload.version is not None and payload.version != event.version:
        raise HTTPException(
            status_code=409,
            detail="Conflict: This event was modified by another household member. Please refresh."
        )

    if payload.title is not None:
        event.title = payload.title
    if payload.description is not None:
        event.description = payload.description
    if payload.location is not None:
        event.location = payload.location
    if payload.start_time is not None:
        event.start_time = payload.start_time
    if payload.end_time is not None:
        event.end_time = payload.end_time
    if payload.is_all_day is not None:
        event.is_all_day = payload.is_all_day
    if payload.category_id is not None:
        event.category_id = payload.category_id
    if payload.recurrence_type is not None:
        event.recurrence_type = payload.recurrence_type
    if payload.recurrence_interval_days is not None:
        event.recurrence_interval_days = payload.recurrence_interval_days
    if payload.status is not None:
        event.status = payload.status
    if payload.reminder_minutes_before is not None:
        event.reminder_minutes_before = payload.reminder_minutes_before

    # Update participants if supplied
    if payload.participant_user_ids is not None:
        active_members = (await db.execute(
            select(HomeMemberModel.user_id).where(
                HomeMemberModel.home_id == home_ctx.home_id,
                HomeMemberModel.user_id.in_(payload.participant_user_ids),
                HomeMemberModel.status == "ACTIVE"
            )
        )).scalars().all()
        active_set = set(active_members)
        for uid in payload.participant_user_ids:
            if uid not in active_set:
                raise HTTPException(
                    status_code=400,
                    detail="All participants must be active members of this home."
                )

        # Retain existing statuses where possible
        existing_status_map = {p.user_id: p.status for p in event.participants}
        event.participants.clear()
        for uid in payload.participant_user_ids:
            event.participants.append(
                EventParticipantModel(
                    event_id=event.id,
                    user_id=uid,
                    status=existing_status_map.get(uid, "INVITED")
                )
            )

    event.version += 1
    await db.commit()
    await db.refresh(event)

    all_user_ids = {event.created_by} | {p.user_id for p in event.participants}
    user_map = {}
    if all_user_ids:
        profiles_res = await db.execute(
            select(UserModel.id, UserProfileModel.first_name, UserProfileModel.last_name, UserProfileModel.avatar_url)
            .outerjoin(UserProfileModel, UserModel.id == UserProfileModel.user_id)
            .where(UserModel.id.in_(all_user_ids))
        )
        for row in profiles_res.all():
            full_name = f"{row.first_name or ''} {row.last_name or ''}".strip() or "Member"
            user_map[row.id] = (full_name, row.avatar_url)

    part_dtos = [
        EventParticipantDTO(
            user_id=p.user_id,
            display_name=user_map.get(p.user_id, ("Member", None))[0],
            avatar_url=user_map.get(p.user_id, ("Member", None))[1],
            status=p.status,
            created_at=p.created_at
        )
        for p in event.participants
    ]

    cat_name = None
    if event.category_id:
        cat = (await db.execute(select(EventCategoryModel).where(EventCategoryModel.id == event.category_id))).scalar_one_or_none()
        if cat:
            cat_name = cat.name

    creator_name, _ = user_map.get(event.created_by, ("Member", None))

    return ApiSuccessResponse(
        data=EventDTO(
            id=event.id,
            home_id=event.home_id,
            category_id=event.category_id,
            category_name=cat_name,
            title=event.title,
            description=event.description,
            location=event.location,
            start_time=event.start_time,
            end_time=event.end_time,
            is_all_day=event.is_all_day,
            recurrence_type=event.recurrence_type,
            recurrence_interval_days=event.recurrence_interval_days,
            parent_recurring_event_id=event.parent_recurring_event_id,
            status=event.status,
            reminder_minutes_before=event.reminder_minutes_before,
            version=event.version,
            created_by=event.created_by,
            created_by_name=creator_name,
            participants=part_dtos,
            created_at=event.created_at,
            updated_at=event.updated_at
        ),
        message="Event updated successfully."
    )


@router.delete("/events/{event_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_event(
    event_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:delete")),
    db: AsyncSession = Depends(get_db),
):
    query = select(EventModel).where(
        EventModel.id == event_id,
        EventModel.home_id == home_ctx.home_id,
        EventModel.deleted_at.is_(None)
    )
    event = (await db.execute(query)).scalar_one_or_none()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")

    event.deleted_at = datetime.now(timezone.utc)
    event.status = "CANCELLED"
    event.version += 1
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message="Event deleted/cancelled successfully.")
    )


@router.post("/events/{event_id}/participants/{user_id}/status", response_model=ApiSuccessResponse[MessageResponse])
async def update_participant_status(
    event_id: UUID,
    user_id: UUID,
    payload: UpdateParticipantStatusRequest,
    home_ctx: HomeContext = Depends(require_home_permission("calendar:view")),
    db: AsyncSession = Depends(get_db),
):
    # Only participant or Home Admin/Owner can update RSVP status
    if home_ctx.user.id != user_id and home_ctx.member.role not in ("OWNER", "ADMIN", "HOME_ADMIN"):
        raise HTTPException(status_code=403, detail="You can only update your own participation status.")

    query = (
        select(EventParticipantModel)
        .join(EventModel, EventParticipantModel.event_id == EventModel.id)
        .where(
            EventParticipantModel.event_id == event_id,
            EventParticipantModel.user_id == user_id,
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None)
        )
    )
    part = (await db.execute(query)).scalar_one_or_none()
    if not part:
        raise HTTPException(status_code=404, detail="Participant record not found.")

    part.status = payload.status
    await db.commit()

    return ApiSuccessResponse(
        data=MessageResponse(message=f"Participation status updated to {payload.status}.")
    )


# ---------------------------------------------------------------------------
# Unified Calendar Projection Endpoint
# ---------------------------------------------------------------------------
@router.get("/calendar/projection", response_model=ApiSuccessResponse[CalendarProjectionResponse])
async def get_calendar_projection(
    start_date: datetime = Query(..., description="Start of projection window (ISO format)"),
    end_date: datetime = Query(..., description="End of projection window (ISO format)"),
    include_tasks: bool = Query(True, description="Include due tasks in projection"),
    include_bills: bool = Query(True, description="Include due bills in projection"),
    home_ctx: HomeContext = Depends(require_home_permission("calendar:view")),
    db: AsyncSession = Depends(get_db),
):
    timeline_items: List[TimelineItemDTO] = []
    total_events = 0
    total_tasks = 0
    total_bills = 0

    # 1. Fetch Calendar Events
    event_query = (
        select(EventModel)
        .options(selectinload(EventModel.category))
        .where(
            EventModel.home_id == home_ctx.home_id,
            EventModel.deleted_at.is_(None),
            EventModel.end_time >= start_date,
            EventModel.start_time <= end_date
        )
    )
    events = (await db.execute(event_query)).scalars().all()
    total_events = len(events)

    for e in events:
        timeline_items.append(
            TimelineItemDTO(
                source_type="EVENT",
                source_id=e.id,
                title=e.title,
                start=e.start_time,
                end=e.end_time,
                all_day=e.is_all_day,
                editable=True,
                navigation_target=f"/calendar/{e.id}",
                status=e.status,
                category_name=e.category.name if e.category else None,
                location=e.location,
                meta_info={
                    "description": e.description,
                    "recurrence_type": e.recurrence_type,
                    "reminder_minutes_before": e.reminder_minutes_before
                }
            )
        )

    # 2. Fetch Tasks (Projection: Zero database duplication)
    if include_tasks:
        start_d = start_date.date()
        end_d = end_date.date()
        task_query = (
            select(TaskModel)
            .options(selectinload(TaskModel.category), selectinload(TaskModel.assignee))
            .where(
                TaskModel.home_id == home_ctx.home_id,
                TaskModel.deleted_at.is_(None),
                TaskModel.status != "COMPLETED",
                TaskModel.due_date.is_not(None),
                TaskModel.due_date >= start_d,
                TaskModel.due_date <= end_d
            )
        )
        tasks = (await db.execute(task_query)).scalars().all()
        total_tasks = len(tasks)

        for t in tasks:
            # Anchor task start & end to due date in UTC
            task_dt = datetime.combine(t.due_date, time(18, 0), tzinfo=timezone.utc)
            timeline_items.append(
                TimelineItemDTO(
                    source_type="TASK",
                    source_id=t.id,
                    title=f"Task: {t.title}",
                    start=task_dt,
                    end=task_dt,
                    all_day=False,
                    editable=False,
                    navigation_target=f"/tasks/{t.id}",
                    status=t.status,
                    category_name=t.category.name if t.category else None,
                    location=None,
                    meta_info={
                        "priority": t.priority,
                        "assigned_to": str(t.assigned_to) if t.assigned_to else None
                    }
                )
            )

    # 3. Fetch Bills (Projection: Zero database duplication)
    if include_bills:
        start_d = start_date.date()
        end_d = end_date.date()
        bill_query = (
            select(BillModel)
            .options(selectinload(BillModel.category))
            .where(
                BillModel.home_id == home_ctx.home_id,
                BillModel.deleted_at.is_(None),
                BillModel.status.in_(["UNPAID", "PARTIALLY_PAID"]),
                BillModel.due_date >= start_d,
                BillModel.due_date <= end_d
            )
        )
        bills = (await db.execute(bill_query)).scalars().all()
        total_bills = len(bills)

        for b in bills:
            # Anchor bill due timestamp
            bill_dt = datetime.combine(b.due_date, time(23, 59, 59), tzinfo=timezone.utc)
            timeline_items.append(
                TimelineItemDTO(
                    source_type="BILL",
                    source_id=b.id,
                    title=f"Bill Due: {b.title} ({b.currency} {b.expected_amount})",
                    start=bill_dt,
                    end=bill_dt,
                    all_day=True,
                    editable=False,
                    navigation_target=f"/bills/{b.id}",
                    status=b.status,
                    category_name=b.category.name if b.category else None,
                    location=None,
                    meta_info={
                        "expected_amount": str(b.expected_amount),
                        "amount_paid": str(b.amount_paid),
                        "currency": b.currency,
                        "responsible_member_id": str(b.responsible_member_id) if b.responsible_member_id else None
                    }
                )
            )

    # Sort all projected timeline items chronologically
    timeline_items.sort(key=lambda item: item.start)

    return ApiSuccessResponse(
        data=CalendarProjectionResponse(
            start_date=start_date,
            end_date=end_date,
            items=timeline_items,
            total_events=total_events,
            total_tasks=total_tasks,
            total_bills=total_bills
        )
    )
