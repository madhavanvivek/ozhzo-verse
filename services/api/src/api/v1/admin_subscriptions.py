import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_current_user, require_super_admin
from src.infrastructure.database.session import get_db
from src.infrastructure.database.models import (
    PromotionModel,
    SubscriptionAuditLogModel,
    SubscriptionFeatureModel,
    SubscriptionPlanFeatureModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.auth import MessageResponse
from src.schemas.subscription import (
    CreatePromotionRequest,
    CreateSubscriptionFeatureRequest,
    CreateSubscriptionPlanRequest,
    CreateSubscriptionPriceRequest,
    PromotionDTO,
    SubscriptionAuditLogDTO,
    SubscriptionFeatureDTO,
    SubscriptionPlanDetailDTO,
    SubscriptionPriceDTO,
    UpdatePromotionRequest,
    UpdateSubscriptionFeatureRequest,
    UpdateSubscriptionPlanRequest,
    UpdateSubscriptionPriceRequest
)

router = APIRouter(prefix="/admin/subscription", tags=["Super Admin - Subscriptions"])


async def record_audit_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: UUID,
    action: str,
    performed_by: UUID,
    old_values: Optional[dict] = None,
    new_values: Optional[dict] = None,
    reason: Optional[str] = None
):
    audit_entry = SubscriptionAuditLogModel(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason
    )
    db.add(audit_entry)


# ------------------------------------------------------------------------------
# 1. Plan Management (Super Admin)
# ------------------------------------------------------------------------------

@router.post("/plans", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[SubscriptionPlanDetailDTO])
async def create_subscription_plan(
    payload: CreateSubscriptionPlanRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    existing_query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.code == payload.code.upper())
    if (await db.execute(existing_query)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Plan with code '{payload.code}' already exists.")

    new_plan = SubscriptionPlanModel(
        name=payload.name,
        code=payload.code.upper(),
        description=payload.description,
        plan_type=payload.plan_type.upper(),
        status="ACTIVE",
        included_members=payload.included_members,
        maximum_members=payload.maximum_members,
        additional_member_allowed=payload.additional_member_allowed,
        introductory_enabled=payload.introductory_enabled,
        introductory_duration_days=payload.introductory_duration_days,
        introductory_price=payload.introductory_price,
        created_by=super_admin.id
    )
    db.add(new_plan)
    await db.flush()

    await record_audit_log(
        db=db,
        entity_type="PLAN",
        entity_id=new_plan.id,
        action="CREATE",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=SubscriptionPlanDetailDTO(
            id=new_plan.id,
            name=new_plan.name,
            code=new_plan.code,
            description=new_plan.description,
            plan_type=new_plan.plan_type,
            status=new_plan.status,
            included_members=new_plan.included_members,
            maximum_members=new_plan.maximum_members,
            additional_member_allowed=new_plan.additional_member_allowed,
            introductory_enabled=new_plan.introductory_enabled,
            introductory_duration_days=new_plan.introductory_duration_days,
            introductory_price=new_plan.introductory_price,
            prices=[],
            features=[]
        )
    )


@router.patch("/plans/{plan_id}", response_model=ApiSuccessResponse[SubscriptionPlanDetailDTO])
async def update_subscription_plan(
    plan_id: UUID,
    payload: UpdateSubscriptionPlanRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(SubscriptionPlanModel, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found.")

    old_state = {
        "name": plan.name,
        "status": plan.status,
        "included_members": plan.included_members,
        "maximum_members": plan.maximum_members,
        "introductory_duration_days": plan.introductory_duration_days,
        "introductory_price": str(plan.introductory_price)
    }

    if payload.name is not None:
        plan.name = payload.name
    if payload.description is not None:
        plan.description = payload.description
    if payload.status is not None:
        plan.status = payload.status.upper()
    if payload.included_members is not None:
        plan.included_members = payload.included_members
    if payload.maximum_members is not None:
        plan.maximum_members = payload.maximum_members
    if payload.additional_member_allowed is not None:
        plan.additional_member_allowed = payload.additional_member_allowed
    if payload.introductory_enabled is not None:
        plan.introductory_enabled = payload.introductory_enabled
    if payload.introductory_duration_days is not None:
        plan.introductory_duration_days = payload.introductory_duration_days
    if payload.introductory_price is not None:
        plan.introductory_price = payload.introductory_price

    plan.updated_at = datetime.now(timezone.utc)
    plan.updated_by = super_admin.id

    await record_audit_log(
        db=db,
        entity_type="PLAN",
        entity_id=plan.id,
        action="UPDATE",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values=payload.model_dump(exclude_unset=True),
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(
        data=SubscriptionPlanDetailDTO(
            id=plan.id,
            name=plan.name,
            code=plan.code,
            description=plan.description,
            plan_type=plan.plan_type,
            status=plan.status,
            included_members=plan.included_members,
            maximum_members=plan.maximum_members,
            additional_member_allowed=plan.additional_member_allowed,
            introductory_enabled=plan.introductory_enabled,
            introductory_duration_days=plan.introductory_duration_days,
            introductory_price=plan.introductory_price,
            prices=[],
            features=[]
        )
    )


# ------------------------------------------------------------------------------
# 2. Standard / List Price Management & Versioning (Super Admin)
# ------------------------------------------------------------------------------

@router.post("/prices", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[SubscriptionPriceDTO])
async def create_subscription_price(
    payload: CreateSubscriptionPriceRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    plan = await db.get(SubscriptionPlanModel, payload.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Subscription plan not found.")

    country_code = payload.country.upper()
    period = payload.billing_period.upper()

    ver_query = (
        select(SubscriptionPriceModel.version)
        .where(
            SubscriptionPriceModel.plan_id == plan.id,
            SubscriptionPriceModel.country == country_code,
            SubscriptionPriceModel.billing_period == period
        )
        .order_by(desc(SubscriptionPriceModel.version))
    )
    latest_version = (await db.execute(ver_query)).scalar() or 0
    new_version = latest_version + 1

    list_price = payload.list_price
    seat_list_price = payload.additional_member_list_price

    new_price = SubscriptionPriceModel(
        plan_id=plan.id,
        country=country_code,
        region=payload.region.upper(),
        currency=payload.currency.upper(),
        billing_period=period,
        list_price=list_price,
        additional_member_list_price=seat_list_price,
        base_price=payload.base_price or list_price,
        additional_member_price=payload.additional_member_price or seat_list_price,
        version=new_version,
        is_active=True,
        effective_from=payload.effective_from or datetime.now(timezone.utc),
        effective_until=payload.effective_until,
        created_by=super_admin.id
    )
    db.add(new_price)
    await db.flush()

    await record_audit_log(
        db=db,
        entity_type="PRICE",
        entity_id=new_price.id,
        action="CREATE_PRICE_VERSION",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=SubscriptionPriceDTO(
            id=new_price.id,
            plan_id=new_price.plan_id,
            country=new_price.country,
            region=new_price.region,
            currency=new_price.currency,
            billing_period=new_price.billing_period,
            list_price=new_price.list_price,
            additional_member_list_price=new_price.additional_member_list_price,
            base_price=new_price.base_price,
            additional_member_price=new_price.additional_member_price,
            version=new_price.version,
            is_active=new_price.is_active,
            effective_from=new_price.effective_from,
            effective_until=new_price.effective_until
        )
    )


@router.patch("/prices/{price_id}", response_model=ApiSuccessResponse[SubscriptionPriceDTO])
async def update_subscription_price(
    price_id: UUID,
    payload: UpdateSubscriptionPriceRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    price = await db.get(SubscriptionPriceModel, price_id)
    if not price:
        raise HTTPException(status_code=404, detail="Price record not found.")

    old_state = {
        "list_price": str(price.list_price),
        "additional_member_list_price": str(price.additional_member_list_price),
        "is_active": price.is_active
    }

    if payload.list_price is not None:
        price.list_price = payload.list_price
    if payload.additional_member_list_price is not None:
        price.additional_member_list_price = payload.additional_member_list_price
    if payload.base_price is not None:
        price.base_price = payload.base_price
    if payload.additional_member_price is not None:
        price.additional_member_price = payload.additional_member_price
    if payload.is_active is not None:
        price.is_active = payload.is_active
    if payload.effective_until is not None:
        price.effective_until = payload.effective_until

    price.updated_at = datetime.now(timezone.utc)

    await record_audit_log(
        db=db,
        entity_type="PRICE",
        entity_id=price.id,
        action="UPDATE_PRICE",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values=payload.model_dump(exclude_unset=True),
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(
        data=SubscriptionPriceDTO(
            id=price.id,
            plan_id=price.plan_id,
            country=price.country,
            region=price.region,
            currency=price.currency,
            billing_period=price.billing_period,
            list_price=price.list_price,
            additional_member_list_price=price.additional_member_list_price,
            base_price=price.base_price,
            additional_member_price=price.additional_member_price,
            version=price.version,
            is_active=price.is_active,
            effective_from=price.effective_from,
            effective_until=price.effective_until
        )
    )


# ------------------------------------------------------------------------------
# 3. Promotions & Discounts Management (Super Admin)
# ------------------------------------------------------------------------------

@router.post("/promotions", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[PromotionDTO])
async def create_promotion(
    payload: CreatePromotionRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(PromotionModel).where(PromotionModel.code == payload.code.upper().strip())
    if (await db.execute(query)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Promotion with code '{payload.code}' already exists.")

    new_promo = PromotionModel(
        name=payload.name,
        code=payload.code.upper().strip(),
        description=payload.description,
        discount_type=payload.discount_type.upper(),
        discount_value=payload.discount_value,
        start_date=payload.start_date or datetime.now(timezone.utc),
        end_date=payload.end_date,
        status=payload.status.upper(),
        currency=payload.currency.upper() if payload.currency else None,
        country=payload.country.upper() if payload.country else None,
        region=payload.region.upper() if payload.region else None,
        applicable_plan_id=payload.applicable_plan_id,
        new_users_only=payload.new_users_only,
        existing_users_allowed=payload.existing_users_allowed,
        maximum_redemptions=payload.maximum_redemptions,
        maximum_redemptions_per_user=payload.maximum_redemptions_per_user,
        minimum_purchase=payload.minimum_purchase,
        created_by=super_admin.id
    )
    db.add(new_promo)
    await db.flush()

    await record_audit_log(
        db=db,
        entity_type="PROMOTION",
        entity_id=new_promo.id,
        action="CREATE_PROMOTION",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=PromotionDTO(
            id=new_promo.id,
            name=new_promo.name,
            code=new_promo.code,
            description=new_promo.description,
            discount_type=new_promo.discount_type,
            discount_value=new_promo.discount_value,
            start_date=new_promo.start_date,
            end_date=new_promo.end_date,
            status=new_promo.status,
            currency=new_promo.currency,
            country=new_promo.country,
            region=new_promo.region,
            new_users_only=new_promo.new_users_only,
            existing_users_allowed=new_promo.existing_users_allowed,
            maximum_redemptions=new_promo.maximum_redemptions,
            redemptions_count=new_promo.redemptions_count
        )
    )


@router.patch("/promotions/{promo_id}", response_model=ApiSuccessResponse[PromotionDTO])
async def update_promotion(
    promo_id: UUID,
    payload: UpdatePromotionRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    promo = await db.get(PromotionModel, promo_id)
    if not promo:
        raise HTTPException(status_code=404, detail="Promotion record not found.")

    old_state = {
        "name": promo.name,
        "discount_type": promo.discount_type,
        "discount_value": str(promo.discount_value),
        "status": promo.status,
        "maximum_redemptions": promo.maximum_redemptions
    }

    if payload.name is not None:
        promo.name = payload.name
    if payload.description is not None:
        promo.description = payload.description
    if payload.discount_type is not None:
        promo.discount_type = payload.discount_type.upper()
    if payload.discount_value is not None:
        promo.discount_value = payload.discount_value
    if payload.status is not None:
        promo.status = payload.status.upper()
    if payload.end_date is not None:
        promo.end_date = payload.end_date
    if payload.maximum_redemptions is not None:
        promo.maximum_redemptions = payload.maximum_redemptions

    promo.updated_at = datetime.now(timezone.utc)

    await record_audit_log(
        db=db,
        entity_type="PROMOTION",
        entity_id=promo.id,
        action="UPDATE_PROMOTION",
        performed_by=super_admin.id,
        old_values=old_state,
        new_values=payload.model_dump(exclude_unset=True),
        reason=payload.reason
    )
    await db.commit()

    return ApiSuccessResponse(
        data=PromotionDTO(
            id=promo.id,
            name=promo.name,
            code=promo.code,
            description=promo.description,
            discount_type=promo.discount_type,
            discount_value=promo.discount_value,
            start_date=promo.start_date,
            end_date=promo.end_date,
            status=promo.status,
            currency=promo.currency,
            country=promo.country,
            region=promo.region,
            new_users_only=promo.new_users_only,
            existing_users_allowed=promo.existing_users_allowed,
            maximum_redemptions=promo.maximum_redemptions,
            redemptions_count=promo.redemptions_count
        )
    )


@router.get("/promotions", response_model=ApiSuccessResponse[List[PromotionDTO]])
async def list_promotions(
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(PromotionModel).order_by(desc(PromotionModel.created_at))
    promos = (await db.execute(query)).scalars().all()

    dtos = [
        PromotionDTO(
            id=p.id,
            name=p.name,
            code=p.code,
            description=p.description,
            discount_type=p.discount_type,
            discount_value=p.discount_value,
            start_date=p.start_date,
            end_date=p.end_date,
            status=p.status,
            currency=p.currency,
            country=p.country,
            region=p.region,
            new_users_only=p.new_users_only,
            existing_users_allowed=p.existing_users_allowed,
            maximum_redemptions=p.maximum_redemptions,
            redemptions_count=p.redemptions_count
        )
        for p in promos
    ]
    return ApiSuccessResponse(data=dtos)


# ------------------------------------------------------------------------------
# 4. Feature Entitlement Management (Super Admin)
# ------------------------------------------------------------------------------

@router.post("/features", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[SubscriptionFeatureDTO])
async def create_subscription_feature(
    payload: CreateSubscriptionFeatureRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(SubscriptionFeatureModel).where(SubscriptionFeatureModel.code == payload.code.upper())
    if (await db.execute(query)).scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Feature with code '{payload.code}' already exists.")

    new_feat = SubscriptionFeatureModel(
        code=payload.code.upper(),
        name=payload.name,
        description=payload.description,
        is_active=True
    )
    db.add(new_feat)
    await db.flush()

    await record_audit_log(
        db=db,
        entity_type="FEATURE",
        entity_id=new_feat.id,
        action="CREATE_FEATURE",
        performed_by=super_admin.id,
        new_values=payload.model_dump()
    )
    await db.commit()

    return ApiSuccessResponse(
        data=SubscriptionFeatureDTO(
            id=new_feat.id,
            code=new_feat.code,
            name=new_feat.name,
            description=new_feat.description,
            is_enabled=True
        )
    )


# ------------------------------------------------------------------------------
# 5. Audit Log Review (Super Admin)
# ------------------------------------------------------------------------------

@router.get("/audit-logs", response_model=ApiSuccessResponse[List[SubscriptionAuditLogDTO]])
async def get_subscription_audit_logs(
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    query = select(SubscriptionAuditLogModel).order_by(desc(SubscriptionAuditLogModel.created_at)).limit(100)
    logs = (await db.execute(query)).scalars().all()

    dtos = [
        SubscriptionAuditLogDTO(
            id=l.id,
            entity_type=l.entity_type,
            entity_id=l.entity_id,
            action=l.action,
            performed_by=l.performed_by,
            old_values=l.old_values,
            new_values=l.new_values,
            reason=l.reason,
            created_at=l.created_at
        )
        for l in logs
    ]
    return ApiSuccessResponse(data=dtos)
