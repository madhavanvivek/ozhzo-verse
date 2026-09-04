import pytest
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

from fastapi import HTTPException
from httpx import AsyncClient

from src.main import app
from src.infrastructure.database.models import (
    UserModel,
    RegionConfigModel,
    FeatureFlagModel,
    InvitationModel,
    AutomationModel,
)
from src.api.v1.admin_regions import list_regions, create_region, update_region, get_region_pricing
from src.api.v1.admin_feature_flags import list_feature_flags, create_feature_flag, update_feature_flag, delete_feature_flag
from src.api.v1.admin_invitations import list_global_invitations, extend_invitation_expiry, revoke_invitation_administratively
from src.api.v1.admin_ai_automations import get_ai_platform_config, update_ai_platform_config, list_quarantined_automations, restore_quarantined_automation, disable_problematic_automation
from src.api.v1.admin_system import get_country_level_analytics, get_retention_and_cohort_metrics, broadcast_system_alert
from src.schemas.admin_operational import (
    CreateRegionConfigRequest,
    UpdateRegionConfigRequest,
    CreateFeatureFlagRequest,
    UpdateFeatureFlagRequest,
    AdminExtendInvitationRequest,
    AdminRevokeInvitationRequest,
    UpdateAdminAIConfigRequest,
    AdminBroadcastAlertRequest,
)
from src.api.dependencies import get_current_user, require_super_admin


# ==============================================================================
# 1. Regional Configuration & Pricing Endpoints
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_regions_lifecycle():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    # Test listing regions with seeded defaults
    mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[
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
            metadata_json={},
        )
    ]))))

    res = await list_regions(super_admin=super_admin, db=mock_db)
    assert res.success is True
    assert len(res.data) >= 1
    assert res.data[0].country_code == "IN"

    # Test creating new region
    create_req = CreateRegionConfigRequest(
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
        metadata_json={},
    )
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    created = await create_region(payload=create_req, super_admin=super_admin, db=mock_db)
    assert created.success is True
    assert created.data.country_code == "AE"
    assert created.data.currency == "AED"


# ==============================================================================
# 2. Feature Flags Management & Targeting
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_feature_flags_crud():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    # List flags
    mock_flag = FeatureFlagModel(
        id=uuid4(),
        key="ai_grocery_smart_ordering",
        name="AI Automated Grocery Reordering",
        description="Proactively drafts shopping list items from pantry expiration events.",
        is_enabled=True,
        target_countries=["IN", "AE"],
        target_plans=["HOME_PRO"],
        rollout_percentage=100,
        rules_json={},
    )
    mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[mock_flag]))))

    flags_res = await list_feature_flags(super_admin=super_admin, db=mock_db)
    assert flags_res.success is True
    assert len(flags_res.data) == 1
    assert flags_res.data[0].key == "ai_grocery_smart_ordering"

    # Create flag
    create_payload = CreateFeatureFlagRequest(
        key="voice_tasks_v2",
        name="Voice Tasks",
        description="Voice memo tasks",
        is_enabled=True,
        target_countries=["US"],
        target_plans=["HOME_PRO"],
        rollout_percentage=50,
        rules_json={},
    )
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=None))

    created = await create_feature_flag(payload=create_payload, super_admin=super_admin, db=mock_db)
    assert created.success is True
    assert created.data.key == "voice_tasks_v2"
    assert created.data.rollout_percentage == 50

    # Update flag
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_flag))
    updated = await update_feature_flag(
        flag_id=mock_flag.id,
        payload=UpdateFeatureFlagRequest(is_enabled=False),
        super_admin=super_admin,
        db=mock_db,
    )
    assert updated.success is True
    assert updated.data.is_enabled is False


# ==============================================================================
# 3. Global Invitations Management
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_global_invitations_operations():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    mock_inv = InvitationModel(
        id=uuid4(),
        home_id=uuid4(),
        invited_by=super_admin.id,
        role="MEMBER",
        token="inv-tok-1",
        invitation_code="OZ-TEST01",
        email="test@family.com",
        phone_number="+919876543210",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=2),
        created_at=datetime.now(timezone.utc),
    )

    # Search invitations
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(mock_inv, "Johnson Family Home", "Super Admin")]))
    res = await list_global_invitations(q="OZ-TEST01", status="PENDING", home_id=None, limit=50, super_admin=super_admin, db=mock_db)
    assert res.success is True
    assert len(res.data) == 1
    assert res.data[0].invitation_code == "OZ-TEST01"

    # Extend expiration
    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_inv))
    ext_res = await extend_invitation_expiry(
        invitation_id=mock_inv.id,
        payload=AdminExtendInvitationRequest(days_to_add=14, reason="User travel delay"),
        super_admin=super_admin,
        db=mock_db,
    )
    assert ext_res.success is True
    assert "extended" in ext_res.data.message.lower()

    # Revoke invitation
    rev_res = await revoke_invitation_administratively(
        invitation_id=mock_inv.id,
        payload=AdminRevokeInvitationRequest(reason="Admin cleanup"),
        super_admin=super_admin,
        db=mock_db,
    )
    assert rev_res.success is True
    assert "revoked" in rev_res.data.message.lower()


# ==============================================================================
# 4. AI & Automations Telemetry & Operations
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_ai_and_automations_controls():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    # AI Config
    mock_db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=450)),  # total_records
        MagicMock(scalar=MagicMock(return_value=Decimal("12.50"))),  # total_cost
        MagicMock(scalar=MagicMock(return_value=320000)),  # total_tokens
        MagicMock(scalar=MagicMock(return_value=18)),  # active_quotas
    ]
    ai_res = await get_ai_platform_config(super_admin=super_admin, db=mock_db)
    assert ai_res.success is True
    assert ai_res.data.total_ai_records == 450
    assert ai_res.data.total_estimated_cost_usd == 12.50

    # Automations Quarantine & Restore
    mock_auto = AutomationModel(
        id=uuid4(),
        home_id=uuid4(),
        name="Auto Restock Pods",
        trigger_type="LOW_STOCK",
        conditions={},
        actions=[],
        schedule={},
        execution_policy={},
        status="ERROR",
        failure_count=5,
        consecutive_failures=5,
        enabled=False,
    )
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(mock_auto, "Smith Home")]))

    q_res = await list_quarantined_automations(super_admin=super_admin, db=mock_db)
    assert q_res.success is True
    assert len(q_res.data) == 1
    assert q_res.data[0]["name"] == "Auto Restock Pods"

    mock_db.execute.return_value = MagicMock(scalar_one_or_none=MagicMock(return_value=mock_auto))
    r_res = await restore_quarantined_automation(automation_id=mock_auto.id, super_admin=super_admin, db=mock_db)
    assert r_res.success is True
    assert "restored" in r_res.data.message.lower()


# ==============================================================================
# 5. Country Analytics, Retention & Broadcast Alert
# ==============================================================================

@pytest.mark.asyncio
async def test_admin_country_and_retention_analytics():
    super_admin = UserModel(id=uuid4(), email="superadmin@ozhzo.com", is_super_admin=True, system_role="SUPER_ADMIN")
    mock_db = AsyncMock()

    # Country metrics
    mock_db.execute.return_value = MagicMock(scalars=MagicMock(return_value=MagicMock(all=MagicMock(return_value=[]))))
    c_res = await get_country_level_analytics(super_admin=super_admin, db=mock_db)
    assert c_res.success is True
    assert len(c_res.data) >= 5

    # Retention metrics
    mock_db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=100)),  # tot_homes
        MagicMock(scalar=MagicMock(return_value=92)),   # act_homes
    ]
    ret_res = await get_retention_and_cohort_metrics(super_admin=super_admin, db=mock_db)
    assert ret_res.success is True
    assert ret_res.data.d1_retention_rate == 88.5
    assert ret_res.data.two_plus_module_adoption_rate == 82.4

    # Broadcast alert
    mock_db.execute.side_effect = None
    mock_db.execute.return_value = MagicMock(all=MagicMock(return_value=[(uuid4(), uuid4())]))
    b_res = await broadcast_system_alert(
        payload=AdminBroadcastAlertRequest(title="Maintenance Notice", message="Servers updating", priority="HIGH"),
        super_admin=super_admin,
        db=mock_db,
    )
    assert b_res.success is True
    assert "dispatched" in b_res.data.message.lower()


# ==============================================================================
# 6. Strict RBAC Barrier for Non-Admins
# ==============================================================================

@pytest.mark.asyncio
async def test_non_admin_rbac_barrier(async_client: AsyncClient):
    # Regular user trying to hit admin endpoints directly
    app.dependency_overrides[get_current_user] = lambda: UserModel(
        id=uuid4(),
        email="normal@ozhzo.com",
        is_super_admin=False,
        system_role="USER"
    )

    try:
        res1 = await async_client.get("/api/v1/admin/regions")
        assert res1.status_code in [401, 403]

        res2 = await async_client.get("/api/v1/admin/feature-flags")
        assert res2.status_code in [401, 403]

        res3 = await async_client.get("/api/v1/admin/invitations")
        assert res3.status_code in [401, 403]

        res4 = await async_client.get("/api/v1/admin/ai/config")
        assert res4.status_code in [401, 403]
    finally:
        app.dependency_overrides.clear()
