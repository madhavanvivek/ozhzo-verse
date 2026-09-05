import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.infrastructure.database.models import (
    SubscriptionPlanModel,
    SubscriptionPriceModel,
    SubscriptionModel,
    UserModel,
)
from src.schemas.subscription import (
    CreateSubscriptionPriceRequest,
    UpdateSubscriptionPriceRequest,
)
from src.api.v1.admin_subscriptions import (
    create_subscription_price,
    update_subscription_price,
    list_subscription_prices,
)
from src.api.v1.subscriptions import (
    get_currency_symbol,
    serialize_subscription_price_dto,
    list_subscription_plans,
)


# ==============================================================================
# Currency Symbol and Metadata Formatting Tests
# ==============================================================================

def test_currency_symbol_formatting():
    """Verify authoritative currency symbols and non-dollar fallbacks."""
    assert get_currency_symbol("AED") == "د.إ"
    assert get_currency_symbol("SAR") == "﷼"
    assert get_currency_symbol("EUR") == "€"
    assert get_currency_symbol("GBP") == "£"
    assert get_currency_symbol("INR") == "₹"
    assert get_currency_symbol("USD") == "$"
    # Unknown currencies must NEVER fallback to '$'
    assert get_currency_symbol("KWD") == "KWD"
    assert get_currency_symbol("XYZ") == "XYZ"
    assert get_currency_symbol(None) == "$"


def test_serialize_subscription_price_dto_sanitization():
    """Verify that serialization fixes legacy corrupted currency symbols and country names."""
    plan_id = uuid4()
    # Simulating a legacy corrupt row with country="AE", currency="AED" but currency_symbol="$" and country_name="Global"
    corrupt_ae_price = SubscriptionPriceModel(
        id=uuid4(),
        plan_id=plan_id,
        country="AE",
        country_name="Global",
        country_iso3="GLB",
        currency="AED",
        currency_symbol="$",  # Corrupted legacy default
        billing_period="ANNUAL",
        regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"),
        additional_member_list_price=Decimal("49.00"),
        offer_price=Decimal("49.00"),
        is_active=True,
        version=1,
    )

    dto = serialize_subscription_price_dto(corrupt_ae_price)
    assert dto.country == "AE"
    assert dto.country_name == "United Arab Emirates"
    assert dto.country_iso3 == "ARE"
    assert dto.currency == "AED"
    assert dto.currency_symbol == "د.إ"  # Sanitized to authoritative AED symbol

    # Simulating a legacy corrupt row with country="SA"
    corrupt_sa_price = SubscriptionPriceModel(
        id=uuid4(),
        plan_id=plan_id,
        country="SA",
        country_name="Global",
        currency="SAR",
        currency_symbol="$",
        billing_period="ANNUAL",
        regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"),
        additional_member_list_price=Decimal("49.00"),
        offer_price=Decimal("49.00"),
        is_active=True,
        version=1,
    )
    dto_sa = serialize_subscription_price_dto(corrupt_sa_price)
    assert dto_sa.country == "SA"
    assert dto_sa.country_name == "Saudi Arabia"
    assert dto_sa.currency == "SAR"
    assert dto_sa.currency_symbol == "﷼"


# ==============================================================================
# Single Canonical Pricing Structure & In-Place Update Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_create_subscription_price_updates_existing_canonical_in_place():
    """
    Super Admin saving a price for an existing country + plan + period updates
    the canonical record in-place and does NOT spawn duplicate version rows.
    """
    mock_db = AsyncMock()
    super_admin = UserModel(id=uuid4(), is_super_admin=True)
    plan_id = uuid4()

    plan = SubscriptionPlanModel(id=plan_id, code="OZHZO_HOME", status="ACTIVE")
    existing_ae_price = SubscriptionPriceModel(
        id=uuid4(),
        plan_id=plan_id,
        country="AE",
        country_name="United Arab Emirates",
        country_iso3="ARE",
        region="MIDDLE_EAST",
        currency="AED",
        currency_symbol="د.إ",
        billing_period="ANNUAL",
        regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"),
        additional_member_list_price=Decimal("49.00"),
        offer_price=Decimal("49.00"),
        tax_percentage=Decimal("0.00"),
        allow_coupon_stacking=False,
        base_price=Decimal("49.00"),
        additional_member_price=Decimal("49.00"),
        offer_status="ACTIVE",
        is_active=True,
        version=1,
    )

    mock_db.get = AsyncMock(return_value=plan)
    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(first=MagicMock(return_value=existing_ae_price))))
    )

    req = CreateSubscriptionPriceRequest(
        plan_id=plan_id,
        country="AE",
        country_name="United Arab Emirates",
        country_iso3="ARE",
        region="MIDDLE_EAST",
        currency="AED",
        currency_symbol="د.إ",
        billing_period="ANNUAL",
        regular_price=Decimal("59.00"),
        list_price=Decimal("59.00"),
        additional_member_list_price=Decimal("59.00"),
        offer_price=Decimal("59.00"),
        tax_percentage=Decimal("0.00"),
    )

    res = await create_subscription_price(req, super_admin=super_admin, db=mock_db)

    assert res.success is True
    # The existing record was updated in-place
    assert existing_ae_price.regular_price == Decimal("59.00")
    assert existing_ae_price.list_price == Decimal("59.00")
    assert existing_ae_price.currency_symbol == "د.إ"
    assert existing_ae_price.is_active is True
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_pricing_deduplication_in_list_endpoints():
    """
    List endpoints return only the canonical active pricing structure per country,
    filtering out legacy duplicates.
    """
    mock_db = AsyncMock()
    super_admin = UserModel(id=uuid4(), is_super_admin=True)
    plan_id = uuid4()

    # Create 3 records for UAE (v1, v2, v3)
    p1 = SubscriptionPriceModel(
        id=uuid4(), plan_id=plan_id, country="AE", billing_period="ANNUAL",
        country_name="United Arab Emirates", country_iso3="ARE", region="MIDDLE_EAST",
        currency="AED", currency_symbol="د.إ", regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"), additional_member_list_price=Decimal("49.00"),
        version=1, is_active=False
    )
    p2 = SubscriptionPriceModel(
        id=uuid4(), plan_id=plan_id, country="AE", billing_period="ANNUAL",
        country_name="United Arab Emirates", country_iso3="ARE", region="MIDDLE_EAST",
        currency="AED", currency_symbol="د.إ", regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"), additional_member_list_price=Decimal("49.00"),
        version=2, is_active=False
    )
    p3 = SubscriptionPriceModel(
        id=uuid4(), plan_id=plan_id, country="AE", billing_period="ANNUAL",
        country_name="United Arab Emirates", country_iso3="ARE", region="MIDDLE_EAST",
        currency="AED", currency_symbol="د.إ", regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"), additional_member_list_price=Decimal("49.00"),
        version=3, is_active=True
    )
    # Plus 1 record for Saudi Arabia
    p_sa = SubscriptionPriceModel(
        id=uuid4(), plan_id=plan_id, country="SA", billing_period="ANNUAL",
        country_name="Saudi Arabia", country_iso3="SAU", region="MIDDLE_EAST",
        currency="SAR", currency_symbol="﷼", regular_price=Decimal("49.00"),
        list_price=Decimal("49.00"), additional_member_list_price=Decimal("49.00"),
        version=1, is_active=True
    )

    mock_db.execute = AsyncMock(
        return_value=MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[p3, p2, p1, p_sa]))))
    )

    res = await list_subscription_prices(super_admin=super_admin, db=mock_db)
    
    assert res.success is True
    # Only 2 distinct country pricing structures returned
    assert len(res.data) == 2
    countries = {p.country for p in res.data}
    assert countries == {"AE", "SA"}
    # The AE price is version 3
    ae_item = next(p for p in res.data if p.country == "AE")
    assert ae_item.version == 3
    assert ae_item.currency_symbol == "د.إ"
