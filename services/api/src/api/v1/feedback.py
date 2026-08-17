from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_home_permission, require_super_admin, HomeContext
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import AuditLogModel, UserModel
from src.schemas.common import ApiSuccessResponse
from src.schemas.feedback import CreateFeedbackRequest, FeedbackDTO, FeedbackListResponse

router = APIRouter(tags=["Pilot Feedback"])


@router.post("/homes/{home_id}/feedback", response_model=ApiSuccessResponse[FeedbackDTO], status_code=status.HTTP_201_CREATED)
async def submit_home_pilot_feedback(
    payload: CreateFeedbackRequest,
    home_ctx: HomeContext = Depends(require_home_permission("home:view")),
    db: AsyncSession = Depends(get_db),
):
    user = home_ctx.user
    user_name = user.profile.display_name if (user and user.profile) else (user.email if user else "Pilot Member")
    log_id = uuid4()
    now = datetime.now(timezone.utc)

    details = {
        "category": payload.category,
        "message": payload.message,
        "rating": payload.rating,
        "app_version": payload.app_version,
        "home_id": str(home_ctx.home_id),
        "user_name": user_name
    }

    audit_entry = AuditLogModel(
        id=log_id,
        entity_type="PILOT_FEEDBACK",
        entity_id=log_id,
        action=f"SUBMIT_{payload.category}",
        performed_by=user.id,
        details=details,
        created_at=now
    )
    db.add(audit_entry)
    await db.commit()

    return ApiSuccessResponse(
        data=FeedbackDTO(
            id=log_id,
            home_id=home_ctx.home_id,
            user_id=user.id,
            user_name=user_name,
            category=payload.category,
            message=payload.message,
            rating=payload.rating,
            app_version=payload.app_version,
            created_at=now
        )
    )


@router.get("/admin/feedback", response_model=ApiSuccessResponse[FeedbackListResponse])
async def list_pilot_feedback_admin(
    limit: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(AuditLogModel)
        .options(selectinload(AuditLogModel.user))
        .where(AuditLogModel.entity_type == "PILOT_FEEDBACK")
        .order_by(AuditLogModel.created_at.desc())
        .limit(limit)
    )
    entries = (await db.execute(query)).scalars().all()

    items: List[FeedbackDTO] = []
    for e in entries:
        d = e.details or {}
        u_name = d.get("user_name") or (e.user.profile.display_name if (e.user and e.user.profile) else "Pilot Member")
        h_id = UUID(d["home_id"]) if "home_id" in d and d["home_id"] else None
        items.append(
            FeedbackDTO(
                id=e.id,
                home_id=h_id,
                user_id=e.performed_by,
                user_name=u_name,
                category=d.get("category", "FEEDBACK"),
                message=d.get("message", ""),
                rating=d.get("rating"),
                app_version=d.get("app_version", "0.1.0-pilot.1"),
                created_at=e.created_at
            )
        )

    return ApiSuccessResponse(
        data=FeedbackListResponse(
            items=items,
            total=len(items)
        )
    )
