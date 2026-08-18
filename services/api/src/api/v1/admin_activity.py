from datetime import datetime, timezone
from typing import Any, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import desc, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    AuditLogModel,
    SubscriptionAuditLogModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.admin import AdminActivityItemDTO

router = APIRouter(prefix="/admin/activity", tags=["Super Admin - Activity"])


def _extract_int_param(param_val: Any, default_val: int) -> int:
    if hasattr(param_val, "default") and not isinstance(param_val, int):
        return int(param_val.default)
    try:
        return int(param_val)
    except (TypeError, ValueError):
        return default_val


def _extract_str_param(param_val: Any, default_val: Optional[str] = None) -> Optional[str]:
    if param_val is None:
        return default_val
    if isinstance(param_val, str):
        return param_val
    if hasattr(param_val, "default") and isinstance(param_val.default, str):
        return param_val.default
    return default_val


@router.get("", response_model=ApiSuccessResponse[List[AdminActivityItemDTO]])
async def list_admin_activity(
    entity_type: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_admin_permission("admin:activity:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    List global platform administrative audit logs across users, homes, subscriptions, and coupons.
    Excludes passwords, tokens, and private secrets.
    """
    lim = _extract_int_param(limit, 50)
    off = _extract_int_param(offset, 0)
    entity_str = _extract_str_param(entity_type)
    action_str = _extract_str_param(action)

    stmt = (
        select(SubscriptionAuditLogModel, UserModel.email.label("actor_email"))
        .outerjoin(UserModel, SubscriptionAuditLogModel.performed_by == UserModel.id)
        .order_by(desc(SubscriptionAuditLogModel.created_at))
    )

    if entity_str:
        stmt = stmt.where(SubscriptionAuditLogModel.entity_type == entity_str.upper().strip())
    if action_str:
        stmt = stmt.where(SubscriptionAuditLogModel.action.ilike(f"%{action_str.strip()}%"))

    stmt = stmt.limit(lim).offset(off)

    res = await db.execute(stmt)
    rows = res.all()

    dtos = [
        AdminActivityItemDTO(
            id=log.id,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            action=log.action,
            performed_by=log.performed_by,
            performed_by_email=actor_email,
            old_values=log.old_values,
            new_values=log.new_values,
            reason=log.reason,
            created_at=log.created_at
        )
        for log, actor_email in rows
    ]

    return ApiSuccessResponse(data=dtos)
