import pytest
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

from src.api.v1.dashboard import get_time_greeting, get_home_dashboard
from src.api.dependencies import HomeContext
from src.domain.permissions import ROLE_OWNER, ROLE_CHILD, ROLE_GUEST
from src.infrastructure.database.models import UserModel, UserProfileModel


def test_time_greeting_logic():
    # Morning: 5 - 11
    assert get_time_greeting(6) == "Good morning"
    assert get_time_greeting(11) == "Good morning"

    # Afternoon: 12 - 16
    assert get_time_greeting(12) == "Good afternoon"
    assert get_time_greeting(16) == "Good afternoon"

    # Evening: 17 - 21
    assert get_time_greeting(17) == "Good evening"
    assert get_time_greeting(21) == "Good evening"

    # Night: 22 - 4
    assert get_time_greeting(22) == "Good night"
    assert get_time_greeting(2) == "Good night"


@pytest.mark.asyncio
async def test_dashboard_child_role_redaction():
    mock_db = AsyncMock()
    home_id = uuid4()
    child_id = uuid4()

    child_profile = UserProfileModel(user_id=child_id, display_name="Leo")
    child_user = UserModel(id=child_id, email="leo@example.com", profile=child_profile)
    ctx = HomeContext(home_id=home_id, user=child_user, role=ROLE_CHILD)

    # Mock DB counts: chores=2, low_stock=1, unpaid_bills=3, members=3
    mock_chores_cnt = MagicMock(); mock_chores_cnt.scalar.return_value = 2
    mock_low_cnt = MagicMock(); mock_low_cnt.scalar.return_value = 1
    mock_bills_cnt = MagicMock(); mock_bills_cnt.scalar.return_value = 3
    mock_bills_sum = MagicMock(); mock_bills_sum.scalar.return_value = Decimal("245.50")
    mock_mem_cnt = MagicMock(); mock_mem_cnt.scalar.return_value = 3

    # Empty list results for items
    mock_items = MagicMock(); mock_items.all.return_value = []
    mock_scalars = MagicMock(); mock_scalars.scalars.return_value.all.return_value = []

    mock_db.execute.side_effect = [
        mock_chores_cnt,
        mock_low_cnt,
        mock_bills_cnt,
        mock_bills_sum,
        mock_mem_cnt,
        mock_items,
        mock_items,
        mock_items,
        mock_items,
        mock_scalars
    ]

    res = await get_home_dashboard(home_id=home_id, home_ctx=ctx, db=mock_db)

    assert res.success is True
    data = res.data
    # For child role, bills financial data is redacted
    assert data.kpis.unpaid_bills_count == 0
    assert data.kpis.unpaid_bills_sum == Decimal("0.00")
    assert len(data.upcoming_bills) == 0
