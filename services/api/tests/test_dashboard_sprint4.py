import pytest
from datetime import datetime, timezone
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock
from decimal import Decimal

from src.domain.permissions import ROLE_OWNER, ROLE_ADMIN, ROLE_CHILD, ROLE_GUEST
from src.api.v1.dashboard import get_home_dashboard, get_time_period_and_greeting
from src.api.dependencies import HomeContext
from src.infrastructure.database.models import HomeModel, UserModel, UserProfileModel


def test_greeting_time_periods():
    period_morning, greet_morning = get_time_period_and_greeting(8)
    assert period_morning == "morning"
    assert "morning" in greet_morning.lower()

    period_afternoon, greet_afternoon = get_time_period_and_greeting(14)
    assert period_afternoon == "afternoon"
    assert "afternoon" in greet_afternoon.lower()

    period_evening, greet_evening = get_time_period_and_greeting(19)
    assert period_evening == "evening"
    assert "evening" in greet_evening.lower()

    period_night, greet_night = get_time_period_and_greeting(23)
    assert period_night == "night"
    assert "night" in greet_night.lower()


@pytest.mark.asyncio
async def test_get_home_dashboard_owner_role():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Skyline Residence", currency="USD", timezone="UTC", created_by=user_id)
    profile = UserProfileModel(user_id=user_id, display_name="Jordan")
    user = UserModel(id=user_id, email="jordan@example.com", profile=profile)

    mock_db.get.return_value = home

    # Mock count queries returning integers/sums
    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 3
    mock_count_res.first.return_value = (2, Decimal("150.00"))
    mock_count_res.scalars.return_value.all.return_value = []

    mock_db.execute.return_value = mock_count_res

    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_OWNER)
    res = await get_home_dashboard(home_ctx=ctx, db=mock_db)

    assert res.success is True
    assert res.data.summary.home_name == "Skyline Residence"
    assert res.data.role == ROLE_OWNER
    assert "Jordan" in res.data.greeting.user_display_name


@pytest.mark.asyncio
async def test_get_home_dashboard_child_privacy():
    mock_db = AsyncMock()
    home_id = uuid4()
    user_id = uuid4()

    home = HomeModel(id=home_id, name="Skyline Residence", currency="USD", timezone="UTC", created_by=uuid4())
    profile = UserProfileModel(user_id=user_id, display_name="Kid Leo")
    user = UserModel(id=user_id, email="leo@example.com", profile=profile)

    mock_db.get.return_value = home

    mock_count_res = MagicMock()
    mock_count_res.scalar.return_value = 2
    mock_count_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_count_res

    ctx = HomeContext(home_id=home_id, user=user, role=ROLE_CHILD)
    res = await get_home_dashboard(home_ctx=ctx, db=mock_db)

    assert res.success is True
    # For CHILD role, upcoming bills must be completely empty and sum is 0
    assert len(res.data.upcoming_bills) == 0
    assert res.data.summary.unpaid_bills_count == 0
    assert res.data.summary.unpaid_bills_sum == Decimal("0.00")
