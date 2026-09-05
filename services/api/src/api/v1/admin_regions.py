import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import List
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import require_admin_permission, require_super_admin
from src.infrastructure.database.models import (
    RegionConfigModel,
    SubscriptionAuditLogModel,
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    UserModel,
)
from src.infrastructure.database.session import get_db
from src.schemas.admin_operational import (
    CreateRegionConfigRequest,
    RegionConfigDTO,
    UpdateRegionConfigRequest,
)
from src.schemas.common import ApiSuccessResponse
from src.schemas.subscription import CreateSubscriptionPriceRequest, SubscriptionPriceDTO
from src.api.v1.subscriptions import serialize_subscription_price_dto

router = APIRouter(prefix="/admin/regions", tags=["Super Admin - Regional Management"])


async def record_audit_log(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    action: str,
    performed_by: str,
    old_values: dict = None,
    new_values: dict = None,
    reason: str = None,
):
    audit_entry = SubscriptionAuditLogModel(
        entity_type=entity_type,
        entity_id=uuid4(),
        action=action,
        performed_by=uuid4(),
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        reason=reason or f"Administrative action on {entity_type} {entity_id}",
    )
    db.add(audit_entry)


@router.get("", response_model=ApiSuccessResponse[List[RegionConfigDTO]])
async def list_regions(
    super_admin: UserModel = Depends(require_admin_permission("admin:subscriptions:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    List all supported commercial regions and countries.
    """
    stmt = select(RegionConfigModel).order_by(RegionConfigModel.country_name)
    result = await db.execute(stmt)
    regions = result.scalars().all()

    # If DB is empty, bootstrap with standard defaults dynamically
    if not regions:
        defaults = [
            RegionConfigModel(
                id=uuid4(),
                country_code="IN",
                country_name="India",
                region="South Asia",
                currency="INR",
                default_plan_code="HOME_STANDARD",
                payment_gateway="RAZORPAY",
                tax_percentage=Decimal("18.00"),
                is_active=True,
                is_default=False,
                promotional_eligibility_enabled=True,
                metadata_json={"emergency_number": "112", "phone_prefix": "+91"},
            ),
            RegionConfigModel(
                id=uuid4(),
                country_code="AE",
                country_name="United Arab Emirates",
                region="Middle East",
                currency="AED",
                default_plan_code="HOME_STANDARD",
                payment_gateway="STRIPE",
                tax_percentage=Decimal("5.00"),
                is_active=True,
                is_default=False,
                promotional_eligibility_enabled=True,
                metadata_json={"emergency_number": "999", "phone_prefix": "+971"},
            ),
            RegionConfigModel(
                id=uuid4(),
                country_code="SA",
                country_name="Saudi Arabia",
                region="Middle East",
                currency="SAR",
                default_plan_code="HOME_STANDARD",
                payment_gateway="STRIPE",
                tax_percentage=Decimal("15.00"),
                is_active=True,
                is_default=False,
                promotional_eligibility_enabled=True,
                metadata_json={"emergency_number": "911", "phone_prefix": "+966"},
            ),
            RegionConfigModel(
                id=uuid4(),
                country_code="GB",
                country_name="United Kingdom",
                region="Europe",
                currency="GBP",
                default_plan_code="HOME_STANDARD",
                payment_gateway="STRIPE",
                tax_percentage=Decimal("20.00"),
                is_active=True,
                is_default=False,
                promotional_eligibility_enabled=True,
                metadata_json={"emergency_number": "999", "phone_prefix": "+44"},
            ),
            RegionConfigModel(
                id=uuid4(),
                country_code="US",
                country_name="United States",
                region="North America",
                currency="USD",
                default_plan_code="HOME_STANDARD",
                payment_gateway="STRIPE",
                tax_percentage=Decimal("0.00"),
                is_active=True,
                is_default=False,
                promotional_eligibility_enabled=True,
                metadata_json={"emergency_number": "911", "phone_prefix": "+1"},
            ),
            RegionConfigModel(
                id=uuid4(),
                country_code="DE",
                country_name="Germany",
                region="Europe",
                currency="EUR",
                default_plan_code="HOME_STANDARD",
                payment_gateway="STRIPE",
                tax_percentage=Decimal("19.00"),
                is_active=True,
                is_default=False,
                promotional_eligibility_enabled=True,
                metadata_json={"emergency_number": "112", "phone_prefix": "+49"},
            ),
            RegionConfigModel(
                id=uuid4(),
                country_code="GLOBAL",
                country_name="Global / Rest of World",
                region="Global",
                currency="USD",
                default_plan_code="HOME_STANDARD",
                payment_gateway="STRIPE",
                tax_percentage=Decimal("0.00"),
                is_active=True,
                is_default=True,
                promotional_eligibility_enabled=True,
                metadata_json={},
            ),
        ]
        for d in defaults:
            db.add(d)
        await db.commit()
        regions = defaults

    return ApiSuccessResponse(data=[RegionConfigDTO.model_validate(r) for r in regions])


@router.post("", status_code=status.HTTP_201_CREATED, response_model=ApiSuccessResponse[RegionConfigDTO])
async def create_region(
    payload: CreateRegionConfigRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Add a new commercial country/region without code deployment.
    """
    code = payload.country_code.strip().upper()
    existing = await db.execute(select(RegionConfigModel).where(RegionConfigModel.country_code == code))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail=f"Region with country code '{code}' already exists.")

    new_region = RegionConfigModel(
        id=uuid4(),
        country_code=code,
        country_name=payload.country_name.strip(),
        region=payload.region.strip(),
        currency=payload.currency.strip().upper(),
        default_plan_code=payload.default_plan_code.strip().upper(),
        payment_gateway=payload.payment_gateway.strip().upper(),
        tax_percentage=payload.tax_percentage,
        is_active=payload.is_active,
        is_default=payload.is_default,
        promotional_eligibility_enabled=payload.promotional_eligibility_enabled,
        metadata_json=payload.metadata_json or {},
    )
    db.add(new_region)

    await record_audit_log(
        db,
        entity_type="REGION_CONFIG",
        entity_id=code,
        action="CREATE_REGION",
        performed_by=str(super_admin.id),
        new_values=payload.model_dump(mode="json"),
    )

    await db.commit()
    await db.refresh(new_region)

    return ApiSuccessResponse(data=RegionConfigDTO.model_validate(new_region))


@router.patch("/{country_code}", response_model=ApiSuccessResponse[RegionConfigDTO])
async def update_region(
    country_code: str,
    payload: UpdateRegionConfigRequest,
    super_admin: UserModel = Depends(require_super_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update regional settings (currency, gateway, taxes, status).
    """
    code = country_code.strip().upper()
    stmt = select(RegionConfigModel).where(RegionConfigModel.country_code == code)
    region = (await db.execute(stmt)).scalar_one_or_none()
    if not region:
        raise HTTPException(status_code=404, detail=f"Region '{code}' not found.")

    old_vals = {
        "country_name": region.country_name,
        "region": region.region,
        "currency": region.currency,
        "default_plan_code": region.default_plan_code,
        "payment_gateway": region.payment_gateway,
        "tax_percentage": str(region.tax_percentage),
        "is_active": region.is_active,
    }

    if payload.country_name is not None:
        region.country_name = payload.country_name.strip()
    if payload.region is not None:
        region.region = payload.region.strip()
    if payload.currency is not None:
        region.currency = payload.currency.strip().upper()
    if payload.default_plan_code is not None:
        region.default_plan_code = payload.default_plan_code.strip().upper()
    if payload.payment_gateway is not None:
        region.payment_gateway = payload.payment_gateway.strip().upper()
    if payload.tax_percentage is not None:
        region.tax_percentage = payload.tax_percentage
    if payload.is_active is not None:
        region.is_active = payload.is_active
    if payload.is_default is not None:
        region.is_default = payload.is_default
    if payload.promotional_eligibility_enabled is not None:
        region.promotional_eligibility_enabled = payload.promotional_eligibility_enabled
    if payload.metadata_json is not None:
        region.metadata_json = payload.metadata_json

    await record_audit_log(
        db,
        entity_type="REGION_CONFIG",
        entity_id=code,
        action="UPDATE_REGION",
        performed_by=str(super_admin.id),
        old_values=old_vals,
        new_values=payload.model_dump(exclude_unset=True, mode="json"),
    )

    await db.commit()
    await db.refresh(region)

    return ApiSuccessResponse(data=RegionConfigDTO.model_validate(region))


@router.get("/{country_code}/pricing", response_model=ApiSuccessResponse[List[SubscriptionPriceDTO]])
async def get_region_pricing(
    country_code: str,
    super_admin: UserModel = Depends(require_admin_permission("admin:subscriptions:view")),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieve all current and historical price versions for a given country code.
    """
    code = country_code.strip().upper()
    stmt = (
        select(SubscriptionPriceModel)
        .where(SubscriptionPriceModel.country == code)
        .order_by(desc(SubscriptionPriceModel.version), desc(SubscriptionPriceModel.created_at))
    )
    res = await db.execute(stmt)
    prices = res.scalars().all()
    return ApiSuccessResponse(data=[serialize_subscription_price_dto(p) for p in prices])
