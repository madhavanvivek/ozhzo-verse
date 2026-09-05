import math
from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, and_
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    CourseModel,
    CourseSessionModel,
    CourseAssignmentModel,
    CourseExamModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.course import (
    CourseDTO,
    CourseDetailDTO,
    CourseSessionDTO,
    CourseAssignmentDTO,
    CourseExamDTO,
    CreateCourseRequest,
    UpdateCourseRequest,
    CreateCourseSessionRequest,
    UpdateCourseSessionRequest,
    CreateCourseAssignmentRequest,
    UpdateCourseAssignmentRequest,
    CreateCourseExamRequest,
    UpdateCourseExamRequest,
    PaginatedCoursesResponse
)

router = APIRouter(prefix="/homes/{home_id}/courses", tags=["Family Learning & Courses"])


def to_course_dto(course: CourseModel) -> CourseDTO:
    return CourseDTO(
        id=course.id,
        home_id=course.home_id,
        title=course.title,
        description=course.description,
        instructor=course.instructor,
        provider=course.provider,
        start_date=course.start_date,
        end_date=course.end_date,
        status=course.status or "ACTIVE",
        color=course.color or "#6366f1",
        created_at=course.created_at,
        updated_at=course.updated_at
    )


def to_session_dto(session: CourseSessionModel) -> CourseSessionDTO:
    return CourseSessionDTO(
        id=session.id,
        course_id=session.course_id,
        home_id=session.home_id,
        title=session.title,
        start_time=session.start_time,
        end_time=session.end_time,
        is_all_day=session.is_all_day,
        location=session.location,
        recurrence_type=session.recurrence_type or "NONE",
        status=session.status or "SCHEDULED",
        notes=session.notes,
        created_at=session.created_at,
        updated_at=session.updated_at
    )


def to_assignment_dto(assignment: CourseAssignmentModel) -> CourseAssignmentDTO:
    return CourseAssignmentDTO(
        id=assignment.id,
        course_id=assignment.course_id,
        home_id=assignment.home_id,
        title=assignment.title,
        description=assignment.description,
        due_date=assignment.due_date,
        status=assignment.status or "PENDING",
        assigned_to=assignment.assigned_to,
        created_at=assignment.created_at,
        updated_at=assignment.updated_at
    )


def to_exam_dto(exam: CourseExamModel) -> CourseExamDTO:
    return CourseExamDTO(
        id=exam.id,
        course_id=exam.course_id,
        home_id=exam.home_id,
        title=exam.title,
        start_time=exam.start_time,
        end_time=exam.end_time,
        location=exam.location,
        status=exam.status or "SCHEDULED",
        notes=exam.notes,
        created_at=exam.created_at,
        updated_at=exam.updated_at
    )


# ==============================================================================
# Course CRUD
# ==============================================================================

@router.get("", response_model=ApiSuccessResponse[PaginatedCoursesResponse])
async def list_courses(
    status: Optional[str] = Query(None, pattern="^(ACTIVE|COMPLETED|PAUSED|DROPPED)$"),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    home_ctx: HomeContext = Depends(require_home_permission("courses:view")),
    db: AsyncSession = Depends(get_db),
):
    filters = [
        CourseModel.home_id == home_ctx.home_id,
        CourseModel.deleted_at.is_(None)
    ]

    if status:
        filters.append(CourseModel.status == status.upper())
    if search:
        filters.append(
            or_(
                CourseModel.title.ilike(f"%{search}%"),
                CourseModel.description.ilike(f"%{search}%"),
                CourseModel.instructor.ilike(f"%{search}%"),
                CourseModel.provider.ilike(f"%{search}%")
            )
        )

    count_query = select(func.count(CourseModel.id)).where(*filters)
    total = (await db.execute(count_query)).scalar_one() or 0

    query = (
        select(CourseModel)
        .where(*filters)
        .order_by(CourseModel.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    courses = (await db.execute(query)).scalars().all()

    total_pages = math.ceil(total / page_size) if total > 0 else 1
    return ApiSuccessResponse(
        data=PaginatedCoursesResponse(
            items=[to_course_dto(c) for c in courses],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )
    )


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[CourseDTO])
async def create_course(
    payload: CreateCourseRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:create")),
    db: AsyncSession = Depends(get_db),
):
    course = CourseModel(
        home_id=home_ctx.home_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        instructor=payload.instructor.strip() if payload.instructor else None,
        provider=payload.provider.strip() if payload.provider else None,
        start_date=payload.start_date,
        end_date=payload.end_date,
        status=payload.status or "ACTIVE",
        color=payload.color or "#6366f1",
        created_by=home_ctx.user.id
    )
    db.add(course)
    await db.commit()
    await db.refresh(course)

    return ApiSuccessResponse(data=to_course_dto(course))


@router.get("/{course_id}", response_model=ApiSuccessResponse[CourseDetailDTO])
async def get_course(
    course_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("courses:view")),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(CourseModel)
        .options(
            selectinload(CourseModel.sessions),
            selectinload(CourseModel.assignments),
            selectinload(CourseModel.exams)
        )
        .where(
            CourseModel.id == course_id,
            CourseModel.home_id == home_ctx.home_id,
            CourseModel.deleted_at.is_(None)
        )
    )
    course = (await db.execute(query)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found or belongs to another household.")

    active_sessions = [s for s in (course.sessions or []) if s.deleted_at is None]
    active_assignments = [a for a in (course.assignments or []) if a.deleted_at is None]
    active_exams = [e for e in (course.exams or []) if e.deleted_at is None]

    active_sessions.sort(key=lambda s: s.start_time)
    active_assignments.sort(key=lambda a: a.due_date)
    active_exams.sort(key=lambda e: e.start_time)

    return ApiSuccessResponse(
        data=CourseDetailDTO(
            id=course.id,
            home_id=course.home_id,
            title=course.title,
            description=course.description,
            instructor=course.instructor,
            provider=course.provider,
            start_date=course.start_date,
            end_date=course.end_date,
            status=course.status or "ACTIVE",
            color=course.color or "#6366f1",
            created_at=course.created_at,
            updated_at=course.updated_at,
            sessions=[to_session_dto(s) for s in active_sessions],
            assignments=[to_assignment_dto(a) for a in active_assignments],
            exams=[to_exam_dto(e) for e in active_exams]
        )
    )


@router.patch("/{course_id}", response_model=ApiSuccessResponse[CourseDTO])
async def update_course(
    course_id: UUID,
    payload: UpdateCourseRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    query = select(CourseModel).where(
        CourseModel.id == course_id,
        CourseModel.home_id == home_ctx.home_id,
        CourseModel.deleted_at.is_(None)
    )
    course = (await db.execute(query)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    if payload.title is not None:
        course.title = payload.title.strip()
    if payload.description is not None:
        course.description = payload.description.strip() if payload.description else None
    if payload.instructor is not None:
        course.instructor = payload.instructor.strip() if payload.instructor else None
    if payload.provider is not None:
        course.provider = payload.provider.strip() if payload.provider else None
    if payload.start_date is not None:
        course.start_date = payload.start_date
    if payload.end_date is not None:
        course.end_date = payload.end_date
    if payload.status is not None:
        course.status = payload.status
    if payload.color is not None:
        course.color = payload.color

    course.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(course)

    return ApiSuccessResponse(data=to_course_dto(course))


@router.delete("/{course_id}")
async def delete_course(
    course_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("courses:delete")),
    db: AsyncSession = Depends(get_db),
):
    query = select(CourseModel).where(
        CourseModel.id == course_id,
        CourseModel.home_id == home_ctx.home_id,
        CourseModel.deleted_at.is_(None)
    )
    course = (await db.execute(query)).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    now = datetime.now(timezone.utc)
    course.deleted_at = now
    await db.commit()

    return ApiSuccessResponse(data={"message": f"Course '{course.title}' deleted successfully."})


# ==============================================================================
# Sessions CRUD
# ==============================================================================

@router.post("/{course_id}/sessions", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[CourseSessionDTO])
async def create_course_session(
    course_id: UUID,
    payload: CreateCourseSessionRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    # Verify course exists
    course = (await db.execute(
        select(CourseModel).where(
            CourseModel.id == course_id,
            CourseModel.home_id == home_ctx.home_id,
            CourseModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    session = CourseSessionModel(
        course_id=course.id,
        home_id=home_ctx.home_id,
        title=payload.title.strip(),
        start_time=payload.start_time,
        end_time=payload.end_time,
        is_all_day=payload.is_all_day,
        location=payload.location.strip() if payload.location else None,
        recurrence_type=payload.recurrence_type or "NONE",
        status=payload.status or "SCHEDULED",
        notes=payload.notes.strip() if payload.notes else None,
        created_by=home_ctx.user.id
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    return ApiSuccessResponse(data=to_session_dto(session))


@router.patch("/{course_id}/sessions/{session_id}", response_model=ApiSuccessResponse[CourseSessionDTO])
async def update_course_session(
    course_id: UUID,
    session_id: UUID,
    payload: UpdateCourseSessionRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    session = (await db.execute(
        select(CourseSessionModel).where(
            CourseSessionModel.id == session_id,
            CourseSessionModel.course_id == course_id,
            CourseSessionModel.home_id == home_ctx.home_id,
            CourseSessionModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Course session not found.")

    if payload.title is not None:
        session.title = payload.title.strip()
    if payload.start_time is not None:
        session.start_time = payload.start_time
    if payload.end_time is not None:
        session.end_time = payload.end_time
    if payload.is_all_day is not None:
        session.is_all_day = payload.is_all_day
    if payload.location is not None:
        session.location = payload.location.strip() if payload.location else None
    if payload.recurrence_type is not None:
        session.recurrence_type = payload.recurrence_type
    if payload.status is not None:
        session.status = payload.status
    if payload.notes is not None:
        session.notes = payload.notes.strip() if payload.notes else None

    session.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(session)

    return ApiSuccessResponse(data=to_session_dto(session))


@router.delete("/{course_id}/sessions/{session_id}")
async def delete_course_session(
    course_id: UUID,
    session_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    session = (await db.execute(
        select(CourseSessionModel).where(
            CourseSessionModel.id == session_id,
            CourseSessionModel.course_id == course_id,
            CourseSessionModel.home_id == home_ctx.home_id,
            CourseSessionModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Course session not found.")

    session.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data={"message": "Course session deleted successfully."})


# ==============================================================================
# Assignments CRUD
# ==============================================================================

@router.post("/{course_id}/assignments", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[CourseAssignmentDTO])
async def create_course_assignment(
    course_id: UUID,
    payload: CreateCourseAssignmentRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    course = (await db.execute(
        select(CourseModel).where(
            CourseModel.id == course_id,
            CourseModel.home_id == home_ctx.home_id,
            CourseModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    assignment = CourseAssignmentModel(
        course_id=course.id,
        home_id=home_ctx.home_id,
        title=payload.title.strip(),
        description=payload.description.strip() if payload.description else None,
        due_date=payload.due_date,
        status=payload.status or "PENDING",
        assigned_to=payload.assigned_to,
        created_by=home_ctx.user.id
    )
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)

    return ApiSuccessResponse(data=to_assignment_dto(assignment))


@router.patch("/{course_id}/assignments/{assignment_id}", response_model=ApiSuccessResponse[CourseAssignmentDTO])
async def update_course_assignment(
    course_id: UUID,
    assignment_id: UUID,
    payload: UpdateCourseAssignmentRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    assignment = (await db.execute(
        select(CourseAssignmentModel).where(
            CourseAssignmentModel.id == assignment_id,
            CourseAssignmentModel.course_id == course_id,
            CourseAssignmentModel.home_id == home_ctx.home_id,
            CourseAssignmentModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Course assignment not found.")

    if payload.title is not None:
        assignment.title = payload.title.strip()
    if payload.description is not None:
        assignment.description = payload.description.strip() if payload.description else None
    if payload.due_date is not None:
        assignment.due_date = payload.due_date
    if payload.status is not None:
        assignment.status = payload.status
    if payload.assigned_to is not None:
        assignment.assigned_to = payload.assigned_to

    assignment.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(assignment)

    return ApiSuccessResponse(data=to_assignment_dto(assignment))


@router.delete("/{course_id}/assignments/{assignment_id}")
async def delete_course_assignment(
    course_id: UUID,
    assignment_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    assignment = (await db.execute(
        select(CourseAssignmentModel).where(
            CourseAssignmentModel.id == assignment_id,
            CourseAssignmentModel.course_id == course_id,
            CourseAssignmentModel.home_id == home_ctx.home_id,
            CourseAssignmentModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not assignment:
        raise HTTPException(status_code=404, detail="Course assignment not found.")

    assignment.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data={"message": "Course assignment deleted successfully."})


# ==============================================================================
# Exams CRUD
# ==============================================================================

@router.post("/{course_id}/exams", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[CourseExamDTO])
async def create_course_exam(
    course_id: UUID,
    payload: CreateCourseExamRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    course = (await db.execute(
        select(CourseModel).where(
            CourseModel.id == course_id,
            CourseModel.home_id == home_ctx.home_id,
            CourseModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found.")

    exam = CourseExamModel(
        course_id=course.id,
        home_id=home_ctx.home_id,
        title=payload.title.strip(),
        start_time=payload.start_time,
        end_time=payload.end_time,
        location=payload.location.strip() if payload.location else None,
        status=payload.status or "SCHEDULED",
        notes=payload.notes.strip() if payload.notes else None,
        created_by=home_ctx.user.id
    )
    db.add(exam)
    await db.commit()
    await db.refresh(exam)

    return ApiSuccessResponse(data=to_exam_dto(exam))


@router.patch("/{course_id}/exams/{exam_id}", response_model=ApiSuccessResponse[CourseExamDTO])
async def update_course_exam(
    course_id: UUID,
    exam_id: UUID,
    payload: UpdateCourseExamRequest,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    exam = (await db.execute(
        select(CourseExamModel).where(
            CourseExamModel.id == exam_id,
            CourseExamModel.course_id == course_id,
            CourseExamModel.home_id == home_ctx.home_id,
            CourseExamModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Course exam not found.")

    if payload.title is not None:
        exam.title = payload.title.strip()
    if payload.start_time is not None:
        exam.start_time = payload.start_time
    if payload.end_time is not None:
        exam.end_time = payload.end_time
    if payload.location is not None:
        exam.location = payload.location.strip() if payload.location else None
    if payload.status is not None:
        exam.status = payload.status
    if payload.notes is not None:
        exam.notes = payload.notes.strip() if payload.notes else None

    exam.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(exam)

    return ApiSuccessResponse(data=to_exam_dto(exam))


@router.delete("/{course_id}/exams/{exam_id}")
async def delete_course_exam(
    course_id: UUID,
    exam_id: UUID,
    home_ctx: HomeContext = Depends(require_home_permission("courses:edit")),
    db: AsyncSession = Depends(get_db),
):
    exam = (await db.execute(
        select(CourseExamModel).where(
            CourseExamModel.id == exam_id,
            CourseExamModel.course_id == course_id,
            CourseExamModel.home_id == home_ctx.home_id,
            CourseExamModel.deleted_at.is_(None)
        )
    )).scalar_one_or_none()
    if not exam:
        raise HTTPException(status_code=404, detail="Course exam not found.")

    exam.deleted_at = datetime.now(timezone.utc)
    await db.commit()

    return ApiSuccessResponse(data={"message": "Course exam deleted successfully."})
