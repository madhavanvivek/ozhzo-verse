import json
from datetime import datetime, timezone
from typing import List
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.models import (
    FeatureFlagModel,
    SubscriptionAuditLogModel,
    UserModel,
)
from src.infrastructure.database.session import get_db
from src.schemas.admin_operational import (
    CreateFeatureFlagRequest,
    FeatureFlagDTO,
    UpdateFeatureFlagRequest,
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse

router = APIRouter(prefix="/admin/feature-flags", tags=["Super Admin - Feature Flags"])


async def record_audit_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: dict = None,
    new_values: dict = None,
    reason: str = None,
):
    audit_entry = SubscriptionAuditLogModel(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason or f"Administrative action on {entity_type}",
    )
    db.add(audit_entry)


@router.get("", response_model=ApiSuccessResponse[List[FeatureFlagDTO]])
async def list_feature_flags(
    super_admin: UserModel = Depends(require_admin_permission("admin:dashboard:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all platform feature flags with targeting rules.
    """
    stmt = select(FeatureFlagModel).order_by(desc(FeatureFlagModel.created_at))
    res = await db.execute(stmt)
    flags = res.scalars().all()

    # Seed initial platform flags if empty
    if not flags:
        initial_flags = [
            FeatureFlagModel(
                id=uuid4(),
                key="dynamic_pricing_v2",
                name="Dynamic Regional Pricing Engine",
                description="Enables automated country-currency pricing calculation at checkout.",
                is_enabled=True,
                target_countries=[],
                target_plans=[],
                rollout_percentage=100,
                rules_json={},
            ),
            FeatureFlagModel(
                id=uuid4(),
                key="ai_grocery_smart_ordering",
                name="AI Automated Grocery Reordering",
                description="Proactively drafts shopping list items from pantry expiration events.",
                is_enabled=True,
                target_countries=["IN", "AE", "US"],
                target_plans=["HOME_PRO", "ENTERPRISE"],
                rollout_percentage=100,
                rules_json={},
            ),
            FeatureFlagModel(
                id=uuid4(),
                key="multi_currency_wallet",
                name="Multi-Currency Family Credits Wallet",
                description="Allows storing and applying non-expiring reservation credits.",
                is_enabled=True,
                target_countries=[],
                target_plans=[],
                rollout_percentage=100,
                rules_json={},
            ),
            FeatureFlagModel(
                id=uuid4(),
                key="voice_assistant_beta",
                name="Voice Task Dictation Beta",
                description="Experimental voice note transcription for chores and shopping lists.",
                is_enabled=False,
                target_countries=["US", "GB"],
                target_plans=["HOME_PRO"],
                rollout_percentage=25,
                rules_json={},
            ),
        ]
        for f in initial_flags:
            db.add(f)
        await db.commit()
        flags = initial_flags

    return ApiSuccessResponse(data=[FeatureFlagDTO.model_validate(f) for f in flags])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[FeatureFlagDTO])
async def create_feature_flag(
    payload: CreateFeatureFlagRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new platform feature flag.
    """
    clean_key = payload.key.strip().lower()
    existing = await db.execute(select(FeatureFlagModel).where(FeatureFlagModel.key == clean_key))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Feature flag with key '{clean_key}' already exists.")

    new_flag = FeatureFlagModel(
        id=uuid4(),
        key=clean_key,
        name=payload.name.strip(),
        description=payload.description,
        is_enabled=payload.is_enabled,
        target_countries=[c.upper() for c in payload.target_countries],
        target_plans=[p.upper() for p in payload.target_plans],
        rollout_percentage=payload.rollout_percentage,
        rules_json=payload.rules_json or {},
        starts_at=payload.starts_at,
        expires_at=payload.expires_at,
        created_by=super_admin.id,
    )
    db.add(new_flag)

    await record_audit_log(
        db,
        entity_type="FEATURE_FLAG",
        entity_id=new_flag.id,
        action="CREATE_FLAG",
        performed_by=super_admin.id,
        new_values=payload.model_dump(mode="json"),
    )

    await db.commit()
    await db.refresh(new_flag)

    return ApiSuccessResponse(data=FeatureFlagDTO.model_validate(new_flag))


@router.patch("/{flag_id}", response_model=ApiSuccessResponse[FeatureFlagDTO])
async def update_feature_flag(
    flag_id: UUID,
    payload: UpdateFeatureFlagRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update feature flag configuration, rollout, or status.
    """
    stmt = select(FeatureFlagModel).where(FeatureFlagModel.id == flag_id)
    flag = (await db.execute(stmt)).scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found.")

    old_vals = {
        "is_enabled": flag.is_enabled,
        "rollout_percentage": flag.rollout_percentage,
        "target_countries": flag.target_countries,
        "target_plans": flag.target_plans,
    }

    if payload.name is not None:
        flag.name = payload.name.strip()
    if payload.description is not None:
        flag.description = payload.description
    if payload.is_enabled is not None:
        flag.is_enabled = payload.is_enabled
    if payload.target_countries is not None:
        flag.target_countries = [c.upper() for c in payload.target_countries]
    if payload.target_plans is not None:
        flag.target_plans = [p.upper() for p in payload.target_plans]
    if payload.rollout_percentage is not None:
        flag.rollout_percentage = payload.rollout_percentage
    if payload.rules_json is not None:
        flag.rules_json = payload.rules_json
    if payload.starts_at is not None:
        flag.starts_at = payload.starts_at
    if payload.expires_at is not None:
        flag.expires_at = payload.expires_at

    await record_audit_log(
        db,
        entity_type="FEATURE_FLAG",
        entity_id=flag.id,
        action="UPDATE_FLAG",
        performed_by=super_admin.id,
        old_values=old_vals,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )

    await db.commit()
    await db.refresh(flag)

    return ApiSuccessResponse(data=FeatureFlagDTO.model_validate(flag))


@router.delete("/{flag_id}", response_model=ApiSuccessResponse[MessageResponse])
async def delete_feature_flag(
    flag_id: UUID,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Deactivate/delete a feature flag.
    """
    stmt = select(FeatureFlagModel).where(FeatureFlagModel.id == flag_id)
    flag = (await db.execute(stmt)).scalar_one_or_none()
    if not flag:
        raise HTTPException(status_code=404, detail="Feature flag not found.")

    await record_audit_log(
        db,
        entity_type="FEATURE_FLAG",
        entity_id=flag.id,
        action="DELETE_FLAG",
        performed_by=super_admin.id,
        old_values={"key": flag.key, "name": flag.name, "is_enabled": flag.is_enabled},
    )

    await db.delete(flag)
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message=f"Feature flag '{flag.key}' deleted successfully."))
