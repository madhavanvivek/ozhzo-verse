from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4
import pytest
from fastapi import HTTPException

from src.api.dependencies import require_home_permission
from src.domain.entitlements import (
    claim_reserved_entitlement,
    provision_first_year_free_entitlement,
    provision_paid_home_entitlement,
    reserve_home_access_entitlement,
    verify_user_home_access_entitlement,
)
from src.infrastructure.database.models import (
    HomeAccessEntitlementModel,
    HomeMemberModel,
    HomeModel,
    SubscriptionModel,
    UserModel,
)


@pytest.mark.asyncio
async def test_rule_a_home_and_data_never_expires():
    """Rule A: Home record and household data remain permanent even if entitlement expires."""
    user_id = uuid4()
    home_id = uuid4()
    user = UserModel(id=user_id, email="owner@ozhzo.com", mobile_verified=True)

    # Expired entitlement (e.g. 400 days ago)
    now = datetime.now(timezone.utc)
    expired_entitlement = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        entitlement_type="FIRST_YEAR_FREE",
        status="ACTIVE",
        starts_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=35),
    )

    home = HomeModel(id=home_id, name="Permanent Home", created_by=user_id, status="ACTIVE")

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = [expired_entitlement]
    mock_db.execute.return_value = mock_res
    mock_db.get.return_value = home

    # Check access entitlement
    is_entitled, ent, reason = await verify_user_home_access_entitlement(user, home_id, mock_db)
    
    # Access is blocked due to expiry
    assert is_entitled is False
    assert ent.status == "EXPIRED"
    assert "expired" in reason.lower()

    # Crucial Rule A Invariant: Home itself is NOT deleted or changed to DELETED
    assert home.status == "ACTIVE"
    assert home.deleted_at is None


@pytest.mark.asyncio
async def test_rule_b_first_home_free_for_first_year():
    """Rule B: First created home receives 1-year FIRST_YEAR_FREE entitlement for creator."""
    user_id = uuid4()
    home_id = uuid4()
    user = UserModel(id=user_id, email="first_home@ozhzo.com", mobile_verified=True, free_home_consumed=False)
    home = HomeModel(id=home_id, name="First Home", created_by=user_id, status="ACTIVE", created_at=datetime.now(timezone.utc))

    mock_db = AsyncMock()
    ent = await provision_first_year_free_entitlement(user, home, mock_db)

    assert ent.home_id == home_id
    assert ent.user_id == user_id
    assert ent.entitlement_type == "FIRST_YEAR_FREE"
    assert ent.status == "ACTIVE"
    # Entitlement validity is ~365 days
    now = datetime.now(timezone.utc)
    assert ent.expires_at > now + timedelta(days=360)


@pytest.mark.asyncio
async def test_rule_c_second_home_requires_paid_subscription():
    """Rule C: Second Home requires paid subscription entitlement."""
    user_id = uuid4()
    home1_id = uuid4()
    home2_id = uuid4()
    user = UserModel(id=user_id, email="multi_home@ozhzo.com", mobile_verified=True, free_home_consumed=True)

    # Home 2 creation requires paid entitlement
    sub_id = uuid4()
    home2 = HomeModel(id=home2_id, name="Second Home", created_by=user_id, status="ACTIVE")

    mock_db = AsyncMock()
    ent = await provision_paid_home_entitlement(user, home2, sub_id, mock_db)

    assert ent.home_id == home2_id
    assert ent.user_id == user_id
    assert ent.subscription_id == sub_id
    assert ent.entitlement_type == "PAID_SEAT"
    assert ent.status == "ACTIVE"


@pytest.mark.asyncio
async def test_rule_d_access_is_user_plus_home_server_enforced():
    """Rule D: Server-side authorization blocks user with active membership but expired entitlement."""
    user_id = uuid4()
    home_id = uuid4()
    user = UserModel(id=user_id, email="member@ozhzo.com", is_super_admin=False, system_role="USER")

    # Member is active in HomeMemberModel
    member = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=user_id, role="MEMBER", status="ACTIVE")

    # But Entitlement is expired
    now = datetime.now(timezone.utc)
    expired_ent = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        entitlement_type="PAID_SEAT",
        status="ACTIVE",
        starts_at=now - timedelta(days=400),
        expires_at=now - timedelta(days=35),
    )

    mock_db = AsyncMock()
    mock_member_res = MagicMock()
    mock_member_res.scalar_one_or_none.return_value = member

    mock_ent_res = MagicMock()
    mock_ent_res.scalars.return_value.all.return_value = [expired_ent]

    mock_db.execute.side_effect = [mock_member_res, mock_ent_res]
    mock_redis = AsyncMock()

    dep = require_home_permission("tasks:view")
    with pytest.raises(HTTPException) as exc_info:
        await dep(home_id=home_id, current_user=user, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_rule_e_each_member_requires_own_entitlement():
    """Rule E: Member A2 in Home X requires their own valid entitlement or allocated seat."""
    owner_id = uuid4()
    member_id = uuid4()
    home_id = uuid4()

    owner = UserModel(id=owner_id, email="owner@ozhzo.com")
    member = UserModel(id=member_id, email="member@ozhzo.com")

    # Owner has valid entitlement
    owner_ent = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=owner_id,
        entitlement_type="FIRST_YEAR_FREE",
        status="ACTIVE",
        expires_at=datetime.now(timezone.utc) + timedelta(days=300),
    )

    mock_db = AsyncMock()
    
    # 1. Owner is authorized
    mock_ent_owner = MagicMock()
    mock_ent_owner.scalars.return_value.all.return_value = [owner_ent]
    mock_db.execute.return_value = mock_ent_owner
    is_owner_entitled, _, _ = await verify_user_home_access_entitlement(owner, home_id, mock_db)
    assert is_owner_entitled is True

    # 2. Member has NO entitlement record and home has no active paid subscription
    mock_ent_empty = MagicMock()
    mock_ent_empty.scalars.return_value.all.return_value = []
    mock_ent_empty.scalar_one_or_none.return_value = None
    mock_ent_empty.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = mock_ent_empty
    home = HomeModel(id=home_id, name="Home X", created_by=owner_id, status="ACTIVE", created_at=datetime.now(timezone.utc) - timedelta(days=400))
    mock_db.get.return_value = home

    is_member_entitled, _, _ = await verify_user_home_access_entitlement(member, home_id, mock_db)
    # Member cannot inherit owner's free entitlement
    assert is_member_entitled is False


@pytest.mark.asyncio
async def test_rule_f_super_admin_is_separate_and_exempt():
    """Rule F: Super Admin operations are exempt from Home subscription entitlements."""
    admin_id = uuid4()
    home_id = uuid4()
    admin_user = UserModel(id=admin_id, email="admin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")

    mock_db = AsyncMock()
    is_authorized, ent, reason = await verify_user_home_access_entitlement(admin_user, home_id, mock_db)

    assert is_authorized is True
    assert "Super Admin platform bypass" in reason


@pytest.mark.asyncio
async def test_subscription_reservation_and_identity_binding():
    """Subscription reservation for verified email/phone binds and activates upon user login."""
    admin_id = uuid4()
    home_id = uuid4()
    sub_id = uuid4()
    mock_db = AsyncMock()

    # 1. Admin reserves seat for verified email
    reservation = await reserve_home_access_entitlement(
        home_id=home_id,
        admin_user_id=admin_id,
        identifier_type="EMAIL",
        identifier_value="invited_family@ozhzo.com",
        subscription_id=sub_id,
        db=mock_db,
    )

    assert reservation.status == "RESERVED"
    assert reservation.reserved_identifier_type == "EMAIL"
    assert reservation.reserved_identifier_value == "invited_family@ozhzo.com"
    assert reservation.user_id is None

    # 2. Intended user authenticates and joins Home
    joining_user = UserModel(
        id=uuid4(),
        email="invited_family@ozhzo.com",
        phone_number="+15551234567",
        mobile_verified=True,
    )

    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = reservation
    mock_db.execute.return_value = mock_res

    # Claim reservation
    claimed = await claim_reserved_entitlement(joining_user, home_id, mock_db)

    assert claimed is not None
    assert claimed.id == reservation.id
    assert claimed.user_id == joining_user.id
    assert claimed.status == "ACTIVE"
    assert claimed.expires_at > datetime.now(timezone.utc) + timedelta(days=360)
