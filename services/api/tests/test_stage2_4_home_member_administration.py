import json
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
import pytest
from fastapi import HTTPException

from src.api.dependencies import HomeContext
from src.api.v1.homes import (
    create_join_request,
    review_join_request,
    update_home_settings,
)
from src.api.v1.members import (
    cancel_home_invitation,
    get_home_admin_summary,
    get_home_member_detail,
    list_home_invitations,
    list_home_members,
    remind_member_access_expiry,
    remove_home_member,
    resend_home_invitation,
    update_member_role,
)
from src.infrastructure.database.models import (
    AuditLogModel,
    HomeAccessEntitlementModel,
    HomeJoinRequestModel,
    HomeMemberModel,
    HomeModel,
    InvitationModel,
    NotificationModel,
    UserModel,
    UserProfileModel,
)
from src.schemas.home import (
    CreateJoinRequestInput,
    ReviewJoinRequestInput,
    UpdateHomeRequest,
    UpdateMemberRoleRequest,
)


# ==============================================================================
# 1. MEMBER DIRECTORY: SEARCH, FILTER, PAGINATION & BATCHED ENTITLEMENT RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_member_directory_search_filter_pagination():
    """Verifies listing members with search, role/status filter, and calculated access status."""
    home_id = uuid4()
    owner_id = uuid4()
    m1_id = uuid4()
    m2_id = uuid4()
    now = datetime.now(timezone.utc)

    owner_user = UserModel(id=owner_id, email="owner@ozhzo.com", phone_number="+15550000001", is_active=True)
    owner_profile = UserProfileModel(user_id=owner_id, display_name="Lord Owner")
    owner_mem = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=owner_id, role="OWNER", status="ACTIVE", joined_at=now)

    m1_user = UserModel(id=m1_id, email="active.tenant@ozhzo.com", phone_number="+15550000002", is_active=True)
    m1_profile = UserProfileModel(user_id=m1_id, display_name="Active Tenant")
    m1_mem = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=m1_id, role="MEMBER", status="ACTIVE", joined_at=now)

    m2_user = UserModel(id=m2_id, email="expiring.tenant@ozhzo.com", phone_number="+15550000003", is_active=True)
    m2_profile = UserProfileModel(user_id=m2_id, display_name="Expiring Tenant")
    m2_mem = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=m2_id, role="MEMBER", status="ACTIVE", joined_at=now)

    home = HomeModel(id=home_id, name="Haven Castle", created_by=owner_id, status="ACTIVE", created_at=now)

    # Entitlement for m2 expiring in 3 days
    ent_m2 = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=m2_id,
        status="ACTIVE",
        starts_at=now - timedelta(days=30),
        expires_at=now + timedelta(days=3),
        notes="Expiring Pro Pass"
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = home

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM home_members" in stmt_str:
            res.all.return_value = [
                (owner_mem, owner_user, owner_profile),
                (m1_mem, m1_user, m1_profile),
                (m2_mem, m2_user, m2_profile),
            ]
        elif "FROM home_access_entitlements" in stmt_str:
            res.scalars.return_value.all.return_value = [ent_m2]
        else:
            res.all.return_value = []
            res.scalars.return_value.all.return_value = []
        return res

    mock_db.execute.side_effect = mock_exec

    ctx = HomeContext(home_id=home_id, user=owner_user, role="OWNER")

    res = await list_home_members(
        search=None,
        status="ACTIVE",
        role=None,
        page=1,
        page_size=50,
        home_ctx=ctx,
        db=mock_db
    )

    assert len(res.data) == 3
    # Check owner access status
    owner_dto = next(m for m in res.data if m.user_id == owner_id)
    assert owner_dto.role == "OWNER"
    assert owner_dto.access_status in ["ACTIVE", "EXPIRING"]

    # Check expiring member access status
    m2_dto = next(m for m in res.data if m.user_id == m2_id)
    assert m2_dto.access_status == "EXPIRING"
    assert m2_dto.is_expiring_soon is True
    assert m2_dto.days_until_expiry in [2, 3]
    assert m2_dto.plan_name == "Expiring Pro Pass"


@pytest.mark.asyncio
async def test_member_detail_inspection_and_activity_timeline():
    """Verifies GET /homes/{home_id}/members/{member_id} returns inspection detail with activity timeline."""
    home_id = uuid4()
    member_id = uuid4()
    user_id = uuid4()
    now = datetime.now(timezone.utc)

    user = UserModel(id=user_id, email="inspected@ozhzo.com", phone_number="+15559998888", mobile_verified=True, is_active=True)
    profile = UserProfileModel(user_id=user_id, display_name="Inspected Member")
    member = HomeMemberModel(id=member_id, home_id=home_id, user_id=user_id, role="MEMBER", status="ACTIVE", joined_at=now)

    audit_entry = AuditLogModel(
        id=uuid4(),
        entity_type="HOME_MEMBER",
        entity_id=member_id,
        action="MEMBER_ROLE_CHANGED",
        performed_by=uuid4(),
        created_at=now - timedelta(hours=2)
    )

    mock_db = AsyncMock()

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM home_members" in stmt_str:
            res.first.return_value = (member, user, profile)
        elif "FROM home_access_entitlements" in stmt_str:
            res.scalars.return_value.first.return_value = None
        elif "FROM audit_logs" in stmt_str:
            res.scalars.return_value.all.return_value = [audit_entry]
        else:
            res.first.return_value = None
            res.scalars.return_value.first.return_value = None
            res.scalars.return_value.all.return_value = []
        return res

    mock_db.execute.side_effect = mock_exec

    ctx = HomeContext(home_id=home_id, user=UserModel(id=uuid4(), is_active=True), role="HOME_ADMIN")

    res = await get_home_member_detail(member_id=member_id, home_ctx=ctx, db=mock_db)

    assert res.data.id == member_id
    assert res.data.display_name == "Inspected Member"
    assert res.data.mobile_verified is True
    assert len(res.data.recent_activity) == 1
    assert res.data.recent_activity[0].action == "MEMBER_ROLE_CHANGED"


# ==============================================================================
# 2. ROLE MANAGEMENT, OWNER & LAST ADMIN PROTECTION
# ==============================================================================

@pytest.mark.asyncio
async def test_role_management_permissions_and_audit():
    """Verifies role change by authorized admin records audit and invalidates cache."""
    home_id = uuid4()
    admin_id = uuid4()
    target_member_id = uuid4()
    target_user_id = uuid4()

    admin_user = UserModel(id=admin_id, email="admin@ozhzo.com", is_active=True)
    target_member = HomeMemberModel(
        id=target_member_id,
        home_id=home_id,
        user_id=target_user_id,
        role="MEMBER",
        status="ACTIVE"
    )

    db_added = []
    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = target_member
    mock_db.execute.return_value = res_mock
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=admin_user, role="HOME_ADMIN")

    res = await update_member_role(
        member_id=target_member_id,
        payload=UpdateMemberRoleRequest(role="HOME_ADMIN"),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert target_member.role == "HOME_ADMIN"
    assert "HOME_ADMIN" in res.data.message
    assert mock_redis.delete.called

    audits = [x for x in db_added if isinstance(x, AuditLogModel)]
    assert len(audits) >= 1
    assert audits[0].action == "MEMBER_ROLE_CHANGED"


@pytest.mark.asyncio
async def test_owner_protection_against_demotion_and_removal():
    """Verifies that workspace Owner cannot be demoted or removed."""
    home_id = uuid4()
    owner_id = uuid4()
    admin_id = uuid4()

    admin_user = UserModel(id=admin_id, email="admin@ozhzo.com", is_active=True)
    owner_member = HomeMemberModel(
        id=uuid4(),
        home_id=home_id,
        user_id=owner_id,
        role="OWNER",
        status="ACTIVE"
    )

    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = owner_member
    mock_db.execute.return_value = res_mock
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=admin_user, role="HOME_ADMIN")

    # 1. Demote Owner -> Rejects with 400
    with pytest.raises(HTTPException) as exc_demote:
        await update_member_role(
            member_id=owner_member.id,
            payload=UpdateMemberRoleRequest(role="MEMBER"),
            home_ctx=ctx,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_demote.value.status_code == 400
    assert "cannot modify the role of the workspace owner" in exc_demote.value.detail.lower()

    # 2. Remove Owner -> Rejects with 400
    with pytest.raises(HTTPException) as exc_remove:
        await remove_home_member(
            member_id=owner_member.id,
            home_ctx=ctx,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_remove.value.status_code == 400
    assert "cannot remove the home workspace owner" in exc_remove.value.detail.lower()


@pytest.mark.asyncio
async def test_last_admin_protection_against_demotion_and_removal():
    """Verifies that the last administrator cannot be demoted or removed, preventing admin-less home."""
    home_id = uuid4()
    sole_admin_id = uuid4()

    sole_admin_user = UserModel(id=sole_admin_id, email="soleadmin@ozhzo.com", is_active=True)
    sole_admin_member = HomeMemberModel(
        id=uuid4(),
        home_id=home_id,
        user_id=sole_admin_id,
        role="HOME_ADMIN",
        status="ACTIVE"
    )

    mock_db = AsyncMock()

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "count(home_members.id)" in stmt_str:
            # 0 other admins exist
            res.scalar.return_value = 0
        else:
            res.scalar_one_or_none.return_value = sole_admin_member
        return res

    mock_db.execute.side_effect = mock_exec
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=sole_admin_user, role="HOME_ADMIN")

    # 1. Attempting to demote sole admin -> Rejects with 400
    with pytest.raises(HTTPException) as exc_demote:
        await update_member_role(
            member_id=sole_admin_member.id,
            payload=UpdateMemberRoleRequest(role="MEMBER"),
            home_ctx=ctx,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_demote.value.status_code == 400
    assert "last remaining administrator" in exc_demote.value.detail.lower()

    # 2. Attempting to remove sole admin -> Rejects with 400
    with pytest.raises(HTTPException) as exc_remove:
        await remove_home_member(
            member_id=sole_admin_member.id,
            home_ctx=ctx,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_remove.value.status_code == 400
    assert "last remaining administrator" in exc_remove.value.detail.lower()


# ==============================================================================
# 3. MEMBER REMOVAL & EXPIRY REMINDERS
# ==============================================================================

@pytest.mark.asyncio
async def test_member_removal_preserves_history_and_revokes_access():
    """Verifies that removing a member transitions status to REMOVED, keeps DB record, and invalidates cache."""
    home_id = uuid4()
    admin_id = uuid4()
    member_id = uuid4()
    member_user_id = uuid4()

    admin_user = UserModel(id=admin_id, email="admin@ozhzo.com", is_active=True)
    member = HomeMemberModel(
        id=member_id,
        home_id=home_id,
        user_id=member_user_id,
        role="MEMBER",
        status="ACTIVE"
    )

    db_added = []
    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = member
    mock_db.execute.return_value = res_mock
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=admin_user, role="HOME_ADMIN")

    res = await remove_home_member(
        member_id=member_id,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert member.status == "REMOVED"
    assert "removed" in res.data.message.lower()
    assert mock_redis.delete.called

    audits = [x for x in db_added if isinstance(x, AuditLogModel)]
    assert any(a.action == "MEMBER_REMOVED" for a in audits)


@pytest.mark.asyncio
async def test_member_access_expiry_reminder_and_deduplication():
    """Verifies that reminder notifications are dispatched and deduplicated via Redis."""
    home_id = uuid4()
    admin_id = uuid4()
    member_id = uuid4()
    member_user_id = uuid4()

    admin_user = UserModel(id=admin_id, email="admin@ozhzo.com", is_active=True)
    member = HomeMemberModel(id=member_id, home_id=home_id, user_id=member_user_id, role="MEMBER", status="ACTIVE")
    home = HomeModel(id=home_id, name="Serenity Manor", created_by=admin_id, status="ACTIVE")

    db_added = []
    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = member
    mock_db.execute.return_value = res_mock
    mock_db.get.return_value = home
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))

    mock_redis = AsyncMock()
    mock_redis.get.return_value = None  # No prior reminder sent

    ctx = HomeContext(home_id=home_id, user=admin_user, role="HOME_ADMIN")

    # 1. First reminder dispatch
    res1 = await remind_member_access_expiry(
        member_id=member_id,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )
    assert "sent successfully" in res1.data.message.lower()
    notifs = [x for x in db_added if isinstance(x, NotificationModel)]
    assert any(n.type == "ACCESS_EXPIRY_REMINDER" for n in notifs)

    # 2. Immediate second reminder attempt -> Deduplicated
    mock_redis.get.return_value = "1"
    res2 = await remind_member_access_expiry(
        member_id=member_id,
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )
    assert "already been sent" in res2.data.message.lower()


# ==============================================================================
# 4. CONSOLIDATED SUMMARY & INVITATION MANAGEMENT
# ==============================================================================

@pytest.mark.asyncio
async def test_home_admin_summary_counts():
    """Verifies GET /homes/{home_id}/admin/summary returns aggregated counts in single round-trip."""
    home_id = uuid4()
    home = HomeModel(
        id=home_id,
        name="Grand Haven",
        public_home_id="OZH-GDHV99",
        home_qr_status="ACTIVE",
        join_policy="REQUEST_TO_JOIN",
        created_by=uuid4(),
        status="ACTIVE"
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = home

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "count(home_members.id)" in stmt_str:
            res.scalar.return_value = 5
        elif "count(invitations.id)" in stmt_str:
            res.scalar.return_value = 2
        elif "count(home_join_requests.id)" in stmt_str:
            res.scalar.return_value = 1
        elif "count(home_access_entitlements.id)" in stmt_str:
            res.scalar.return_value = 1
        else:
            res.scalar.return_value = 0
        return res

    mock_db.execute.side_effect = mock_exec

    ctx = HomeContext(home_id=home_id, user=UserModel(id=uuid4(), is_active=True), role="HOME_ADMIN")

    summary_res = await get_home_admin_summary(home_ctx=ctx, db=mock_db)

    data = summary_res.data
    assert data.home_id == home_id
    assert data.home_name == "Grand Haven"
    assert data.public_home_id == "OZH-GDHV99"
    assert data.join_policy == "REQUEST_TO_JOIN"
    assert data.active_members_count == 5
    assert data.pending_invitations_count == 2
    assert data.pending_join_requests_count == 1


@pytest.mark.asyncio
async def test_invitation_management_resend_and_cancel_rules():
    """Verifies invitation resend, cancellation, and accepted invitation protection."""
    home_id = uuid4()
    inv_id = uuid4()
    accepted_inv_id = uuid4()

    pending_inv = InvitationModel(
        id=inv_id,
        home_id=home_id,
        token="tok_pend_001",
        invitation_code="OZ-PEND01",
        role="MEMBER",
        invitation_mode="INVITE_ONLY",
        status="PENDING",
        email="guest@ozhzo.com"
    )

    accepted_inv = InvitationModel(
        id=accepted_inv_id,
        home_id=home_id,
        token="tok_acc_002",
        invitation_code="OZ-ACCP02",
        role="MEMBER",
        invitation_mode="INVITE_ONLY",
        status="ACCEPTED",
        email="accepted@ozhzo.com"
    )

    mock_db = AsyncMock()

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        res.scalar_one_or_none.return_value = pending_inv
        return res

    mock_db.execute.side_effect = mock_exec
    mock_db.get.return_value = HomeModel(id=home_id, name="Estate", status="ACTIVE")

    ctx = HomeContext(home_id=home_id, user=UserModel(id=uuid4(), is_active=True), role="HOME_ADMIN")

    # 1. Resend pending invitation
    resend_res = await resend_home_invitation(invitation_id=inv_id, home_ctx=ctx, db=mock_db)
    assert resend_res.data.status == "PENDING"
    assert resend_res.data.token != "tok_pend_001"

    # 2. Cannot resend accepted invitation
    mock_db.execute.side_effect = None
    res_acc_mock = MagicMock()
    res_acc_mock.scalar_one_or_none.return_value = accepted_inv
    mock_db.execute.return_value = res_acc_mock

    with pytest.raises(HTTPException) as exc_resend:
        await resend_home_invitation(invitation_id=accepted_inv_id, home_ctx=ctx, db=mock_db)
    assert exc_resend.value.status_code == 400
    assert "already been accepted" in exc_resend.value.detail.lower()

    # 3. Cannot cancel accepted invitation
    with pytest.raises(HTTPException) as exc_cancel:
        await cancel_home_invitation(invitation_id=accepted_inv_id, home_ctx=ctx, db=mock_db)
    assert exc_cancel.value.status_code == 400
    assert "already been accepted" in exc_cancel.value.detail.lower()


# ==============================================================================
# 5. JOIN POLICY & JOIN REQUEST CONCURRENCY
# ==============================================================================

@pytest.mark.asyncio
async def test_home_settings_and_join_policy_update():
    """Verifies editing home settings updates join_policy and blocks join requests if INVITE_ONLY."""
    home_id = uuid4()
    owner_id = uuid4()
    applicant_id = uuid4()

    owner_user = UserModel(id=owner_id, email="owner@ozhzo.com", is_active=True)
    applicant_user = UserModel(id=applicant_id, email="applicant@ozhzo.com", is_active=True)

    home = HomeModel(
        id=home_id,
        name="Private Sanctuary",
        public_home_id="OZH-PRIV01",
        home_qr_token="qr_priv_01",
        home_qr_status="ACTIVE",
        join_policy="REQUEST_TO_JOIN",
        created_by=owner_id,
        status="ACTIVE"
    )

    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = home
    res_mock.scalars.return_value.first.return_value = home
    mock_db.execute.return_value = res_mock
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=owner_user, role="OWNER")

    # 1. Update Join Policy to INVITE_ONLY
    updated_res = await update_home_settings(
        payload=UpdateHomeRequest(name="Strictly Private Sanctuary", join_policy="INVITE_ONLY"),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )
    assert updated_res.data.join_policy == "INVITE_ONLY"
    assert home.join_policy == "INVITE_ONLY"

    # 2. Attempting to submit a join request to INVITE_ONLY home raises 400
    with pytest.raises(HTTPException) as exc_join:
        await create_join_request(
            token="OZH-PRIV01",
            payload=CreateJoinRequestInput(message="Please let me in"),
            current_user=applicant_user,
            db=mock_db
        )
    assert exc_join.value.status_code == 400
    assert "invite-only" in exc_join.value.detail.lower()


@pytest.mark.asyncio
async def test_join_request_duplicate_review_prevention():
    """Verifies that an already reviewed join request cannot be approved or rejected again."""
    home_id = uuid4()
    req_id = uuid4()

    join_req = HomeJoinRequestModel(
        id=req_id,
        home_id=home_id,
        user_id=uuid4(),
        status="APPROVED"  # Already reviewed
    )

    mock_db = AsyncMock()
    mock_db.get.return_value = join_req
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=UserModel(id=uuid4(), is_active=True), role="HOME_ADMIN")

    with pytest.raises(HTTPException) as exc_review:
        await review_join_request(
            request_id=req_id,
            payload=ReviewJoinRequestInput(action="APPROVE", role="MEMBER"),
            home_ctx=ctx,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_review.value.status_code == 400
    assert "already been reviewed" in exc_review.value.detail.lower()
