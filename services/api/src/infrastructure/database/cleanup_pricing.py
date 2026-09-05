import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Dict, List, Tuple
from uuid import uuid4

from sqlalchemy import select, func, desc, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.database.session import AsyncSessionLocal
from src.infrastructure.database.models import (
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    SubscriptionModel,
    RegionConfigModel,
)
from src.api.v1.subscriptions import COUNTRY_METADATA_DEFAULTS, CURRENCY_SYMBOLS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pricing_cleanup")

# Canonical default prices specification per country
CANONICAL_DEFAULT_PRICES = {
    "IN": {
        "country_name": "India",
        "country_iso3": "IND",
        "region": "SOUTH_ASIA",
        "currency": "INR",
        "currency_symbol": "₹",
        "regular_price": Decimal("499.00"),
        "list_price": Decimal("499.00"),
        "additional_member_list_price": Decimal("499.00"),
        "offer_price": Decimal("499.00"),
        "tax_percentage": Decimal("0.00"),
        "campaign_name": None,
        "offer_status": "ACTIVE",
    },
    "AE": {
        "country_name": "United Arab Emirates",
        "country_iso3": "ARE",
        "region": "MIDDLE_EAST",
        "currency": "AED",
        "currency_symbol": "د.إ",
        "regular_price": Decimal("49.00"),
        "list_price": Decimal("49.00"),
        "additional_member_list_price": Decimal("49.00"),
        "offer_price": Decimal("49.00"),
        "tax_percentage": Decimal("0.00"),
        "campaign_name": None,
        "offer_status": "ACTIVE",
    },
    "DE": {
        "country_name": "Germany",
        "country_iso3": "DEU",
        "region": "EUROPE",
        "currency": "EUR",
        "currency_symbol": "€",
        "regular_price": Decimal("49.00"),
        "list_price": Decimal("49.00"),
        "additional_member_list_price": Decimal("19.00"),
        "offer_price": Decimal("39.00"),
        "tax_percentage": Decimal("19.00"),
        "campaign_name": "Germany Launch Offer",
        "campaign_description": "Launch promotional rate for German households",
        "offer_status": "ACTIVE",
    },
    "GB": {
        "country_name": "United Kingdom",
        "country_iso3": "GBR",
        "region": "EUROPE",
        "currency": "GBP",
        "currency_symbol": "£",
        "regular_price": Decimal("24.99"),
        "list_price": Decimal("24.99"),
        "additional_member_list_price": Decimal("16.00"),
        "offer_price": Decimal("16.00"),
        "tax_percentage": Decimal("20.00"),
        "campaign_name": "Launch Offer 2026",
        "offer_status": "ACTIVE",
    },
    "SA": {
        "country_name": "Saudi Arabia",
        "country_iso3": "SAU",
        "region": "MIDDLE_EAST",
        "currency": "SAR",
        "currency_symbol": "﷼",
        "regular_price": Decimal("49.00"),
        "list_price": Decimal("49.00"),
        "additional_member_list_price": Decimal("49.00"),
        "offer_price": Decimal("49.00"),
        "tax_percentage": Decimal("15.00"),
        "campaign_name": None,
        "offer_status": "ACTIVE",
    },
    "US": {
        "country_name": "United States",
        "country_iso3": "USA",
        "region": "NORTH_AMERICA",
        "currency": "USD",
        "currency_symbol": "$",
        "regular_price": Decimal("29.99"),
        "list_price": Decimal("29.99"),
        "additional_member_list_price": Decimal("20.00"),
        "offer_price": Decimal("20.00"),
        "tax_percentage": Decimal("0.00"),
        "campaign_name": "Launch Offer 2026",
        "offer_status": "ACTIVE",
    },
    "GLOBAL": {
        "country_name": "Global / Rest of World",
        "country_iso3": "GLB",
        "region": "GLOBAL",
        "currency": "USD",
        "currency_symbol": "$",
        "regular_price": Decimal("29.99"),
        "list_price": Decimal("29.99"),
        "additional_member_list_price": Decimal("20.00"),
        "offer_price": Decimal("20.00"),
        "tax_percentage": Decimal("0.00"),
        "campaign_name": "Launch Offer 2026",
        "offer_status": "ACTIVE",
    },
}


async def run_pricing_cleanup(db: AsyncSession) -> Dict[str, any]:
    """
    Idempotent audit and consolidation of SubscriptionPriceModel records:
    1. Audits all pricing rows.
    2. Consolidates duplicate records per (plan_id, country, billing_period), keeping the canonical latest record.
    3. Archives older duplicate records without breaking historical foreign key references.
    4. Fixes corrupted currency symbols (e.g. '$' for AED/SAR) and country names.
    5. Ensures all required commercial countries (AE, DE, GB, IN, SA, US, GLOBAL) exist with canonical prices.
    """
    logger.info("Starting Regional Pricing Audit & Consolidation...")

    # Fetch default plan
    plan_query = select(SubscriptionPlanModel).where(SubscriptionPlanModel.code == "OZHZO_HOME")
    plan = (await db.execute(plan_query)).scalar_one_or_none()
    if not plan:
        plan_query_any = select(SubscriptionPlanModel).order_by(SubscriptionPlanModel.created_at.asc())
        plan = (await db.execute(plan_query_any)).scalars().first()

    if not plan:
        plan = SubscriptionPlanModel(
            id=uuid4(),
            name="Ozhzo Home Standard",
            code="OZHZO_HOME",
            description="The complete digital operating system for households.",
            plan_type="HOME",
            status="ACTIVE",
            included_members=1,
            maximum_members=10,
            additional_member_allowed=True,
            introductory_enabled=True,
            introductory_duration_days=365,
            introductory_price=Decimal("0.00"),
        )
        db.add(plan)
        await db.flush()

    # Query all prices
    prices_query = select(SubscriptionPriceModel).order_by(
        SubscriptionPriceModel.country.asc(),
        SubscriptionPriceModel.billing_period.asc(),
        desc(SubscriptionPriceModel.version),
        desc(SubscriptionPriceModel.updated_at),
    )
    all_prices = (await db.execute(prices_query)).scalars().all()
    logger.info(f"Total pricing rows found in DB: {len(all_prices)}")

    # Check referenced price IDs in subscriptions
    sub_prices_query = select(SubscriptionModel.price_id).where(SubscriptionModel.price_id.isnot(None))
    referenced_price_ids = set((await db.execute(sub_prices_query)).scalars().all())

    # Group by (plan_id, country, billing_period)
    grouped: Dict[Tuple[str, str, str], List[SubscriptionPriceModel]] = {}
    for p in all_prices:
        key = (str(p.plan_id), p.country.upper(), p.billing_period.upper())
        grouped.setdefault(key, []).append(p)

    retained_records = []
    archived_records = []
    fixed_currency_symbols = []

    for key, price_list in grouped.items():
        plan_id, country_code, billing_period = key
        # Pick the canonical record: highest version / most recent active
        canonical = price_list[0]
        canonical.is_active = True

        # Correct country metadata and currency symbol
        c_meta = COUNTRY_METADATA_DEFAULTS.get(country_code, {})
        spec = CANONICAL_DEFAULT_PRICES.get(country_code, {})
        canonical.country = country_code

        # Name & ISO3
        canonical.country_name = spec.get("country_name") or c_meta.get("name") or canonical.country_name or country_code
        canonical.country_iso3 = spec.get("country_iso3") or c_meta.get("iso3") or canonical.country_iso3 or country_code[:3]
        
        # Currency & Symbol
        curr_upper = (spec.get("currency") or canonical.currency or c_meta.get("currency") or "USD").upper()
        canonical.currency = curr_upper
        canonical.currency_symbol = spec.get("currency_symbol") or CURRENCY_SYMBOLS.get(curr_upper, c_meta.get("symbol", curr_upper))
        
        if spec.get("region"):
            canonical.region = spec["region"]

        # Ensure canonical pricing values if empty
        if canonical.regular_price == Decimal("0.00") and spec.get("regular_price"):
            canonical.regular_price = spec["regular_price"]
            canonical.list_price = spec["list_price"]
            canonical.additional_member_list_price = spec["additional_member_list_price"]
            canonical.offer_price = spec["offer_price"]

        retained_records.append(canonical)
        fixed_currency_symbols.append((country_code, canonical.currency, canonical.currency_symbol))

        # Handle duplicates
        for duplicate in price_list[1:]:
            duplicate.is_active = False
            archived_records.append(duplicate)
            logger.info(
                f"Archived duplicate price row id={duplicate.id} for {country_code} (v{duplicate.version})"
            )

    # Ensure all required canonical countries exist
    existing_countries = {p.country.upper() for p in retained_records}
    for req_code, req_spec in CANONICAL_DEFAULT_PRICES.items():
        if req_code not in existing_countries:
            new_p = SubscriptionPriceModel(
                id=uuid4(),
                plan_id=plan.id,
                country=req_code,
                country_name=req_spec["country_name"],
                country_iso3=req_spec["country_iso3"],
                region=req_spec["region"],
                currency=req_spec["currency"],
                currency_symbol=req_spec["currency_symbol"],
                billing_period="ANNUAL",
                regular_price=req_spec["regular_price"],
                list_price=req_spec["list_price"],
                additional_member_list_price=req_spec["additional_member_list_price"],
                offer_price=req_spec["offer_price"],
                campaign_name=req_spec.get("campaign_name"),
                campaign_description=req_spec.get("campaign_description"),
                offer_status=req_spec.get("offer_status", "ACTIVE"),
                offer_start_date=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
                offer_end_date=datetime(2026, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                tax_percentage=req_spec["tax_percentage"],
                allow_coupon_stacking=False,
                base_price=req_spec["regular_price"],
                additional_member_price=req_spec["additional_member_list_price"],
                version=1,
                is_active=True,
            )
            db.add(new_p)
            retained_records.append(new_p)
            logger.info(f"Created canonical pricing record for {req_code} ({req_spec['currency']})")

    # Ensure RegionConfigModel exists for all canonical countries
    for req_code, req_spec in CANONICAL_DEFAULT_PRICES.items():
        reg_stmt = select(RegionConfigModel).where(RegionConfigModel.country_code == req_code)
        reg_obj = (await db.execute(reg_stmt)).scalar_one_or_none()
        if not reg_obj:
            reg_obj = RegionConfigModel(
                id=uuid4(),
                country_code=req_code,
                country_name=req_spec["country_name"],
                region=req_spec["region"],
                currency=req_spec["currency"],
                default_plan_code="OZHZO_HOME",
                payment_gateway="RAZORPAY" if req_code == "IN" else "STRIPE",
                tax_percentage=req_spec["tax_percentage"],
                is_active=True,
                is_default=(req_code == "GLOBAL"),
                promotional_eligibility_enabled=True,
                metadata_json={},
            )
            db.add(reg_obj)
        else:
            reg_obj.country_name = req_spec["country_name"]
            reg_obj.currency = req_spec["currency"]
            reg_obj.tax_percentage = req_spec["tax_percentage"]
            reg_obj.is_active = True

    await db.commit()

    report = {
        "total_records_initial": len(all_prices),
        "retained_canonical_count": len(retained_records),
        "archived_duplicate_count": len(archived_records),
        "active_country_pricing_count": len({p.country.upper() for p in retained_records if p.is_active}),
        "currencies_verified": fixed_currency_symbols,
    }
    logger.info(f"Pricing Cleanup Report: {report}")
    return report


if __name__ == "__main__":
    async def main():
        async with AsyncSessionLocal() as db:
            rep = await run_pricing_cleanup(db)
            print("CLEANUP SUCCESSFUL:", rep)

    asyncio.run(main())
