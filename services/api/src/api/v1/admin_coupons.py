import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    CampaignModel,
    CouponModel,
    CouponRedemptionModel,
    HomeModel,
    SubscriptionAuditLogModel,
    SubscriptionGrantModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse
from src.schemas.coupon import (
    CampaignDTO,
    CouponAnalyticsDTO,
    CouponDTO,
    CouponRedemptionDTO,
    CreateCampaignRequest,
    CreateCouponRequest,
    CreateSubscriptionGrantRequest,
    SubscriptionGrantDTO,
    UpdateCampaignRequest,
    UpdateCouponRequest
)

router = APIRouter(prefix="/admin", tags=["Super Admin - Coupons, Campaigns & Grants"])


async def record_coupon_audit(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    reason: Optional[str] = None
):
    log = SubscriptionAuditLogModel(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason
    )
    db.add(log)


# ------------------------------------------------------------------------------
# 1. Coupons Management (Super Admin)
# ------------------------------------------------------------------------------

@router.post("/coupons", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[CouponDTO])
async def create_coupon(
    payload: CreateCouponRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(CouponModel).where(CouponModel.code == payload.code.upper().strip())
    if (await db.execute(query)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Coupon with code '{payload.code}' already exists.")

    new_coupon = CouponModel(
        id=uuid4(),
        campaign_id=payload.campaign_id,
        name=payload.name,
        code=payload.code.upper().strip(),
        description=payload.description,
        coupon_type=payload.coupon_type.upper(),
        discount_value=payload.discount_value,
        free_period_value=payload.free_period_value,
        free_period_unit=payload.free_period_unit.upper(),
        eligibility_type=payload.eligibility_type.upper(),
        target_user_id=payload.target_user_id,
        target_home_id=payload.target_home_id,
        country=payload.country.upper() if payload.country else None,
        state=payload.state,
        district=payload.district,
        postal_code=payload.postal_code,
        currency=payload.currency.upper() if payload.currency else None,
        applicable_plan_id=payload.applicable_plan_id,
        start_date=payload.start_date or datetime.now(timezone.utc),
        end_date=payload.end_date,
        maximum_total_redemptions=payload.maximum_total_redemptions,
        maximum_redemptions_per_user=payload.maximum_redemptions_per_user,
        maximum_redemptions_per_home=payload.maximum_redemptions_per_home,
        allow_stacking=payload.allow_stacking,
        status=payload.status.upper(),
        notes=payload.notes,
        internal_reason=payload.internal_reason,
        created_by=super_admin.id
    )
    db.add(new_coupon)
    await db.flush()

    await record_coupon_audit(
        db=db,
        entity_type="COUPON",
        entity_id=new_coupon.id,
        action="CREATE_COUPON",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=CouponDTO(
            id=new_coupon.id,
            campaign_id=new_coupon.campaign_id,
            name=new_coupon.name,
            code=new_coupon.code,
            description=new_coupon.description,
            coupon_type=new_coupon.coupon_type,
            discount_value=new_coupon.discount_value,
            free_period_value=new_coupon.free_period_value,
            free_period_unit=new_coupon.free_period_unit,
            eligibility_type=new_coupon.eligibility_type,
            target_user_id=new_coupon.target_user_id,
            target_home_id=new_coupon.target_home_id,
            country=new_coupon.country,
            state=new_coupon.state,
            district=new_coupon.district,
            postal_code=new_coupon.postal_code,
            currency=new_coupon.currency,
            applicable_plan_id=new_coupon.applicable_plan_id,
            start_date=new_coupon.start_date,
            end_date=new_coupon.end_date,
            maximum_total_redemptions=new_coupon.maximum_total_redemptions,
            redemptions_count=new_coupon.redemptions_count or 0,
            maximum_redemptions_per_user=new_coupon.maximum_redemptions_per_user or 1,
            maximum_redemptions_per_home=new_coupon.maximum_redemptions_per_home or 1,
            allow_stacking=bool(new_coupon.allow_stacking),
            status=new_coupon.status,
            notes=new_coupon.notes,
            internal_reason=new_coupon.internal_reason,
            created_at=new_coupon.created_at or datetime.now(timezone.utc),
            updated_at=new_coupon.updated_at or datetime.now(timezone.utc)
        )
    )


@router.patch("/coupons/{coupon_id}", response_model=ApiSuccessResponse[CouponDTO])
async def update_coupon(
    coupon_id: UUID,
    payload: UpdateCouponRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    coupon = await db.get(CouponModel, coupon_id)
    if not coupon:
        raise HTTPException(status_code=404, detail="Coupon not found.")

    old_state = {
        "name": coupon.name,
        "coupon_type": coupon.coupon_type,
        "discount_value": str(coupon.discount_value),
        "free_period_value": coupon.free_period_value,
        "status": coupon.status
    }

    if payload.name is not None:
        coupon.name = payload.name
    if payload.description is not None:
        coupon.description = payload.description
    if payload.coupon_type is not None:
        coupon.coupon_type = payload.coupon_type.upper()
    if payload.discount_value is not None:
        coupon.discount_value = payload.discount_value
    if payload.free_period_value is not None:
        coupon.free_period_value = payload.free_period_value
    if payload.free_period_unit is not None:
        coupon.free_period_unit = payload.free_period_unit.upper()
    if payload.status is not None:
        coupon.status = payload.status.upper()
    if payload.end_date is not None:
        coupon.end_date = payload.end_date
    if payload.maximum_total_redemptions is not None:
        coupon.maximum_total_redemptions = payload.maximum_total_redemptions
    if payload.maximum_redemptions_per_user is not None:
        coupon.maximum_redemptions_per_user = payload.maximum_redemptions_per_user
    if payload.maximum_redemptions_per_home is not None:
        coupon.maximum_redemptions_per_home = payload.maximum_redemptions_per_home
    if payload.notes is not None:
        coupon.notes = payload.notes
    if payload.internal_reason is not None:
        coupon.internal_reason = payload.internal_reason

    coupon.updated_at = datetime.now(timezone.utc)

    await record_coupon_audit(
        db=db,
        entity_type="COUPON",
        entity_id=coupon.id,
        action="UPDATE_COUPON",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values=payload.model_dump(exclude_unset=True),
        reason=payload.internal_reason
    )
    await db.commit()

    return ApiSuccessResponse(
        data=CouponDTO(
            id=coupon.id,
            campaign_id=coupon.campaign_id,
            name=coupon.name,
            code=coupon.code,
            description=coupon.description,
            coupon_type=coupon.coupon_type,
            discount_value=coupon.discount_value,
            free_period_value=coupon.free_period_value,
            free_period_unit=coupon.free_period_unit,
            eligibility_type=coupon.eligibility_type,
            target_user_id=coupon.target_user_id,
            target_home_id=coupon.target_home_id,
            country=coupon.country,
            state=coupon.state,
            district=coupon.district,
            postal_code=coupon.postal_code,
            currency=coupon.currency,
            applicable_plan_id=coupon.applicable_plan_id,
            start_date=coupon.start_date,
            end_date=coupon.end_date,
            maximum_total_redemptions=coupon.maximum_total_redemptions,
            redemptions_count=coupon.redemptions_count,
            maximum_redemptions_per_user=coupon.maximum_redemptions_per_user,
            maximum_redemptions_per_home=coupon.maximum_redemptions_per_home,
            allow_stacking=coupon.allow_stacking,
            status=coupon.status,
            notes=coupon.notes,
            internal_reason=coupon.internal_reason,
            created_at=coupon.created_at,
            updated_at=coupon.updated_at
        )
    )


@router.get("/coupons", response_model=ApiSuccessResponse[List[CouponDTO]])
async def list_coupons(
    query: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    campaign_id: Optional[UUID] = Query(None),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CouponModel).order_by(desc(CouponModel.created_at)).limit(limit).offset(offset)
    if query:
        stmt = stmt.where(CouponModel.code.ilike(f"%{query.strip()}%") | CouponModel.name.ilike(f"%{query.strip()}%"))
    if status:
        stmt = stmt.where(CouponModel.status == status.upper())
    if campaign_id:
        stmt = stmt.where(CouponModel.campaign_id == campaign_id)

    coupons = (await db.execute(stmt)).scalars().all()

    dtos = [
        CouponDTO(
            id=c.id,
            campaign_id=c.campaign_id,
            name=c.name,
            code=c.code,
            description=c.description,
            coupon_type=c.coupon_type,
            discount_value=c.discount_value,
            free_period_value=c.free_period_value,
            free_period_unit=c.free_period_unit,
            eligibility_type=c.eligibility_type,
            target_user_id=c.target_user_id,
            target_home_id=c.target_home_id,
            country=c.country,
            state=c.state,
            district=c.district,
            postal_code=c.postal_code,
            currency=c.currency,
            applicable_plan_id=c.applicable_plan_id,
            start_date=c.start_date,
            end_date=c.end_date,
            maximum_total_redemptions=c.maximum_total_redemptions,
            redemptions_count=c.redemptions_count,
            maximum_redemptions_per_user=c.maximum_redemptions_per_user,
            maximum_redemptions_per_home=c.maximum_redemptions_per_home,
            allow_stacking=c.allow_stacking,
            status=c.status,
            notes=c.notes,
            internal_reason=c.internal_reason,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in coupons
    ]
    return ApiSuccessResponse(data=dtos)


@router.get("/coupons/{coupon_id}/redemptions", response_model=ApiSuccessResponse[List[CouponRedemptionDTO]])
async def get_coupon_redemptions(
    coupon_id: UUID,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(CouponRedemptionModel, CouponModel.code)
        .join(CouponModel, CouponRedemptionModel.coupon_id == CouponModel.id)
        .where(CouponRedemptionModel.coupon_id == coupon_id)
        .order_by(desc(CouponRedemptionModel.redeemed_at))
    )
    rows = (await db.execute(stmt)).all()

    dtos = [
        CouponRedemptionDTO(
            id=r.id,
            coupon_id=r.coupon_id,
            coupon_code=c_code,
            campaign_id=r.campaign_id,
            user_id=r.user_id,
            home_id=r.home_id,
            discount_amount_applied=r.discount_amount_applied,
            free_days_granted=r.free_days_granted,
            redeemed_at=r.redeemed_at
        )
        for r, c_code in rows
    ]
    return ApiSuccessResponse(data=dtos)


# ------------------------------------------------------------------------------
# 2. Campaigns Management (Super Admin)
# ------------------------------------------------------------------------------

@router.post("/campaigns", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[CampaignDTO])
async def create_campaign(
    payload: CreateCampaignRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(CampaignModel).where(CampaignModel.code == payload.code.upper().strip())
    if (await db.execute(query)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Campaign with code '{payload.code}' already exists.")

    new_campaign = CampaignModel(
        id=uuid4(),
        name=payload.name,
        code=payload.code.upper().strip(),
        description=payload.description,
        status=payload.status.upper(),
        start_date=payload.start_date or datetime.now(timezone.utc),
        end_date=payload.end_date,
        budget_limit=payload.budget_limit,
        maximum_redemptions=payload.maximum_redemptions,
        redemptions_count=0,
        country=payload.country.upper() if payload.country else None,
        state=payload.state,
        created_by=super_admin.id
    )
    db.add(new_campaign)
    await db.flush()

    await record_coupon_audit(
        db=db,
        entity_type="CAMPAIGN",
        entity_id=new_campaign.id,
        action="CREATE_CAMPAIGN",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=CampaignDTO(
            id=new_campaign.id,
            name=new_campaign.name,
            code=new_campaign.code,
            description=new_campaign.description,
            status=new_campaign.status,
            start_date=new_campaign.start_date,
            end_date=new_campaign.end_date,
            budget_limit=new_campaign.budget_limit,
            maximum_redemptions=new_campaign.maximum_redemptions,
            redemptions_count=new_campaign.redemptions_count,
            country=new_campaign.country,
            state=new_campaign.state,
            created_at=new_campaign.created_at,
            updated_at=new_campaign.updated_at
        )
    )


@router.get("/campaigns", response_model=ApiSuccessResponse[List[CampaignDTO]])
async def list_campaigns(
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(CampaignModel).order_by(desc(CampaignModel.created_at))
    campaigns = (await db.execute(stmt)).scalars().all()

    dtos = [
        CampaignDTO(
            id=c.id,
            name=c.name,
            code=c.code,
            description=c.description,
            status=c.status,
            start_date=c.start_date,
            end_date=c.end_date,
            budget_limit=c.budget_limit,
            maximum_redemptions=c.maximum_redemptions,
            redemptions_count=c.redemptions_count,
            country=c.country,
            state=c.state,
            created_at=c.created_at,
            updated_at=c.updated_at
        )
        for c in campaigns
    ]
    return ApiSuccessResponse(data=dtos)


# ------------------------------------------------------------------------------
# 3. Direct Super Admin Grants
# ------------------------------------------------------------------------------

@router.post("/grants", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[SubscriptionGrantDTO])
async def create_direct_grant(
    payload: CreateSubscriptionGrantRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    home = await db.get(HomeModel, payload.home_id)
    if not home:
        raise HTTPException(status_code=404, detail="Home workspace not found.")

    # Lookup plan
    plan = None
    if payload.plan_id:
        plan = await db.get(SubscriptionPlanModel, payload.plan_id)
    if not plan:
        plan = (await db.execute(select(SubscriptionPlanModel).where(SubscriptionPlanModel.code == "OZHZO_HOME"))).scalar_one_or_none()

    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found.")

    now = datetime.now(timezone.utc)
    unit_upper = payload.duration_unit.upper()
    if unit_upper == "DAYS":
        days_to_add = payload.duration_value
    elif unit_upper == "MONTHS":
        days_to_add = payload.duration_value * 30
    elif unit_upper == "YEARS":
        days_to_add = payload.duration_value * 365
    else:
        days_to_add = payload.duration_value * 30

    expiry_date = now + timedelta(days=days_to_add)

    grant = SubscriptionGrantModel(
        id=uuid4(),
        user_id=payload.user_id,
        home_id=payload.home_id,
        plan_id=plan.id,
        grant_type=payload.grant_type.upper(),
        duration_value=payload.duration_value,
        duration_unit=unit_upper,
        discount_value=payload.discount_value,
        start_date=now,
        expiry_date=expiry_date,
        status="ACTIVE",
        reason=payload.reason,
        granted_by=super_admin.id
    )
    db.add(grant)
    await db.flush()

    # Update Home Subscription Entitlement directly
    sub_query = select(SubscriptionModel).where(SubscriptionModel.home_id == payload.home_id)
    sub = (await db.execute(sub_query)).scalar_one_or_none()
    if sub:
        sub.active_grant_id = grant.id
        sub.status = "ACTIVE"
        sub.is_free_period_active = (payload.grant_type == "FREE_PERIOD")
        sub.free_period_ends_at = expiry_date
        sub.updated_at = now

    await record_coupon_audit(
        db=db,
        entity_type="DIRECT_GRANT",
        entity_id=grant.id,
        action="CREATE_DIRECT_GRANT",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=SubscriptionGrantDTO(
            id=grant.id,
            user_id=grant.user_id,
            home_id=grant.home_id,
            plan_id=grant.plan_id,
            grant_type=grant.grant_type,
            duration_value=grant.duration_value,
            duration_unit=grant.duration_unit,
            discount_value=grant.discount_value,
            start_date=grant.start_date,
            expiry_date=grant.expiry_date,
            status=grant.status,
            reason=grant.reason,
            granted_by=grant.granted_by,
            created_at=grant.created_at or datetime.now(timezone.utc),
            updated_at=grant.updated_at or datetime.now(timezone.utc)
        )
    )


@router.get("/grants", response_model=ApiSuccessResponse[List[SubscriptionGrantDTO]])
async def list_direct_grants(
    home_id: Optional[UUID] = Query(None),
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(SubscriptionGrantModel).order_by(desc(SubscriptionGrantModel.created_at))
    if home_id:
        stmt = stmt.where(SubscriptionGrantModel.home_id == home_id)
    grants = (await db.execute(stmt)).scalars().all()

    dtos = [
        SubscriptionGrantDTO(
            id=g.id,
            user_id=g.user_id,
            home_id=g.home_id,
            plan_id=g.plan_id,
            grant_type=g.grant_type,
            duration_value=g.duration_value,
            duration_unit=g.duration_unit,
            discount_value=g.discount_value,
            start_date=g.start_date,
            expiry_date=g.expiry_date,
            status=g.status,
            reason=g.reason,
            granted_by=g.granted_by,
            created_at=g.created_at,
            updated_at=g.updated_at
        )
        for g in grants
    ]
    return ApiSuccessResponse(data=dtos)


@router.post("/grants/{grant_id}/revoke", response_model=ApiSuccessResponse[MessageResponse])
async def revoke_direct_grant(
    grant_id: UUID,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    grant = await db.get(SubscriptionGrantModel, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found.")

    grant.status = "REVOKED"
    grant.updated_at = datetime.now(timezone.utc)

    # Revert home subscription if active
    sub = (await db.execute(select(SubscriptionModel).where(SubscriptionModel.home_id == grant.home_id))).scalar_one_or_none()
    if sub and sub.active_grant_id == grant.id:
        sub.is_free_period_active = False
        sub.status = "RENEWAL_REQUIRED"

    await record_coupon_audit(
        db=db,
        entity_type="DIRECT_GRANT",
        entity_id=grant.id,
        action="REVOKE_DIRECT_GRANT",
        performed_by=super_admin.id,
        reason="Revoked by Super Admin"
    )
    await db.commit()

    return ApiSuccessResponse(data=MessageResponse(message="Subscription grant revoked successfully."))


# ------------------------------------------------------------------------------
# 4. Coupon Analytics Overview
# ------------------------------------------------------------------------------

@router.get("/coupons/analytics", response_model=ApiSuccessResponse[CouponAnalyticsDTO])
async def get_coupon_analytics(
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    tot_coupons = (await db.execute(select(func.count(CouponModel.id)))).scalar() or 0
    act_coupons = (await db.execute(select(func.count(CouponModel.id)).where(CouponModel.status == "ACTIVE"))).scalar() or 0
    exp_coupons = (await db.execute(select(func.count(CouponModel.id)).where(CouponModel.status == "EXPIRED"))).scalar() or 0
    tot_campaigns = (await db.execute(select(func.count(CampaignModel.id)))).scalar() or 0
    tot_redemptions = (await db.execute(select(func.count(CouponRedemptionModel.id)))).scalar() or 0
    tot_grants = (await db.execute(select(func.count(SubscriptionGrantModel.id)))).scalar() or 0
    act_grants = (await db.execute(select(func.count(SubscriptionGrantModel.id)).where(SubscriptionGrantModel.status == "ACTIVE"))).scalar() or 0

    free_users = (await db.execute(select(func.count(CouponRedemptionModel.id)).where(CouponRedemptionModel.free_days_granted > 0))).scalar() or 0
    paid_conv = tot_redemptions - free_users
    conv_rate = float(tot_redemptions / tot_coupons) if tot_coupons > 0 else 0.0

    return ApiSuccessResponse(
        data=CouponAnalyticsDTO(
            total_coupons=tot_coupons,
            active_coupons=act_coupons,
            expired_coupons=exp_coupons,
            total_campaigns=tot_campaigns,
            total_redemptions=tot_redemptions,
            free_users_generated=free_users,
            paid_conversions=max(0, paid_conv),
            coupon_conversion_rate=round(conv_rate, 2),
            total_direct_grants=tot_grants,
            active_direct_grants=act_grants,
            generated_at=datetime.now(timezone.utc)
        )
    )
