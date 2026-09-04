import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4
import pytest
from fastapi import HTTPException

from src.core.home_identity import generate_unique_public_home_id, generate_home_qr_token
from src.domain.entitlements import (
    claim_reserved_entitlement,
    reserve_home_access_entitlement,
    verify_user_home_access_entitlement,
)
from src.infrastructure.database.models import (
    AuditLogModel,
    HomeAccessEntitlementModel,
    HomeJoinRequestModel,
    HomeMemberModel,
    HomeModel,
    InvitationModel,
    NotificationModel,
    SubscriptionModel,
    SubscriptionPlanModel,
    UserModel,
    UserProfileModel,
)
from src.api.v1.homes import (
    create_join_request,
    regenerate_home_qr,
    resolve_home_qr,
    review_join_request,
    revoke_home_qr,
    update_home_settings,
)
from src.api.v1.members import (
    _execute_join_invitation,
    accept_invitation,
    cancel_home_invitation,
    create_invitation,
    decline_invitation,
    leave_home_workspace,
    remove_home_member,
    update_member_role,
)
from src.schemas.home import (
    CreateInvitationRequest,
    CreateJoinRequestInput,
    ReviewJoinRequestInput,
    UpdateHomeRequest,
    UpdateMemberRoleRequest,
)
from src.api.dependencies import HomeContext


# ==============================================================================
# 1. HOME UNIQUE IDENTITY & QR MANAGEMENT
# ==============================================================================

@pytest.mark.asyncio
async def test_home_public_id_and_qr_generation():
    """Verifies public_home_id format (OZH-XXXXXX), QR token generation, and immutability."""
    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = None
    res_mock.scalars.return_value.first.return_value = None
    mock_db.execute.return_value = res_mock

    public_id = await generate_unique_public_home_id(mock_db)
    assert public_id.startswith("OZH-")
    assert len(public_id) == 10

    qr_tok = generate_home_qr_token()
    assert len(qr_tok) >= 32

    # Immutability test: updating home name does NOT change public_home_id or home_qr_token
    user_id = uuid4()
    home_id = uuid4()
    home = HomeModel(
        id=home_id,
        name="Original Manor",
        public_home_id="OZH-ALPHA1",
        home_qr_token="qr_tok_permanent_123",
        home_qr_status="ACTIVE",
        created_by=user_id,
        status="ACTIVE"
    )

    home_res_mock = MagicMock()
    home_res_mock.scalar_one_or_none.return_value = home
    mock_db.get.return_value = home
    mock_db.execute.return_value = home_res_mock

    user = UserModel(id=user_id, email="owner@example.com", is_active=True)
    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")
    mock_redis = AsyncMock()

    res = await update_home_settings(
        payload=UpdateHomeRequest(name="Renamed Manor"),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert res.data.name == "Renamed Manor"
    assert res.data.public_home_id == "OZH-ALPHA1"
    assert "qr_tok_permanent_123" in (res.data.home_qr_url or "")


@pytest.mark.asyncio
async def test_qr_regeneration_and_revocation():
    """Verifies QR token regeneration (version bump, audit log) and revocation."""
    user_id = uuid4()
    home_id = uuid4()
    home = HomeModel(
        id=home_id,
        name="Villa Nova",
        public_home_id="OZH-VILL01",
        home_qr_token="old_qr_tok_111",
        home_qr_status="ACTIVE",
        home_qr_version=1,
        created_by=user_id,
        status="ACTIVE"
    )

    db_added = []
    mock_db = AsyncMock()
    mock_db.get.return_value = home
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))

    user = UserModel(id=user_id, email="owner@example.com", is_active=True)
    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")

    # 1. Regenerate QR token
    regen_res = await regenerate_home_qr(home_ctx=ctx, db=mock_db)
    assert regen_res.data.qr_version == 2
    assert regen_res.data.qr_token != "old_qr_tok_111"
    assert regen_res.data.qr_status == "ACTIVE"
    assert home.home_qr_token == regen_res.data.qr_token

    # 2. Revoke QR token
    revoke_res = await revoke_home_qr(home_ctx=ctx, db=mock_db)
    assert revoke_res.data.qr_status == "REVOKED"
    assert home.home_qr_status == "REVOKED"
    assert home.home_qr_revoked_at is not None

    # Check audit records
    audits = [x for x in db_added if isinstance(x, AuditLogModel)]
    actions = [a.action for a in audits]
    assert "HOME_QR_REGENERATED" in actions
    assert "HOME_QR_REVOKED" in actions


# ==============================================================================
# 2. UNIFIED QR & PUBLIC HOME ID RESOLUTION
# ==============================================================================

@pytest.mark.asyncio
async def test_unified_public_resolve_by_qr_and_public_id():
    """Verifies that resolve_home_qr supports lookup by QR token AND public_home_id."""
    home_id = uuid4()
    owner_id = uuid4()
    owner = UserModel(id=owner_id, email="admin@family.com", is_active=True)
    home = HomeModel(
        id=home_id,
        name="Highland House",
        public_home_id="OZH-HIGH99",
        home_qr_token="secure_highland_token_99",
        home_qr_status="ACTIVE",
        created_by=owner_id,
        status="ACTIVE",
        members=[HomeMemberModel(id=uuid4(), home_id=home_id, user_id=owner_id, status="ACTIVE", role="OWNER")]
    )

    mock_db = AsyncMock()

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM homes" in stmt_str:
            res.scalars.return_value.first.return_value = home
        elif "FROM users" in stmt_str:
            res.scalars.return_value.first.return_value = owner
        return res

    mock_db.execute.side_effect = mock_exec

    # 1. Lookup by QR token
    res_qr = await resolve_home_qr(token="secure_highland_token_99", db=mock_db)
    assert res_qr.data.home_id == home_id
    assert res_qr.data.home_name == "Highland House"
    assert res_qr.data.public_home_id == "OZH-HIGH99"

    # 2. Lookup by human-friendly Public Home ID (case-insensitive)
    res_id = await resolve_home_qr(token="ozh-high99", db=mock_db)
    assert res_id.data.home_id == home_id
    assert res_id.data.public_home_id == "OZH-HIGH99"


@pytest.mark.asyncio
async def test_join_request_lifecycle_and_approval():
    """Verifies join request submission via public_home_id and admin approval/rejection."""
    home_id = uuid4()
    owner_id = uuid4()
    applicant_id = uuid4()
    req_id = uuid4()

    owner = UserModel(id=owner_id, email="admin@ozhzo.com", is_active=True)
    applicant = UserModel(id=applicant_id, email="applicant@ozhzo.com", is_active=True)
    home = HomeModel(
        id=home_id,
        name="Oak Manor",
        public_home_id="OZH-OAK777",
        home_qr_token="oak_token_777",
        home_qr_status="ACTIVE",
        created_by=owner_id,
        status="ACTIVE"
    )

    join_req = HomeJoinRequestModel(
        id=req_id,
        home_id=home_id,
        user_id=applicant_id,
        status="PENDING",
        message="Hello, please let me join!"
    )

    db_added = []
    mock_db = AsyncMock()

    def mock_get(model, pk):
        if model == HomeModel and pk == home_id:
            return home
        if model == HomeJoinRequestModel and pk == req_id:
            return join_req
        return None

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM homes" in stmt_str:
            res.scalars.return_value.first.return_value = home
            res.scalar_one_or_none.return_value = home
        elif "FROM home_members" in stmt_str:
            res.scalars.return_value.first.return_value = None
            res.scalars.return_value.all.return_value = [HomeMemberModel(user_id=owner_id, role="OWNER")]
            res.scalar_one_or_none.return_value = None
        elif "FROM home_join_requests" in stmt_str:
            res.scalars.return_value.first.return_value = None
        else:
            res.scalars.return_value.first.return_value = None
            res.scalar_one_or_none.return_value = None
        return res

    mock_db.get.side_effect = mock_get
    mock_db.execute.side_effect = mock_exec
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))

    # 1. Applicant submits join request using Public Home ID
    created_req = await create_join_request(
        token="OZH-OAK777",
        payload=CreateJoinRequestInput(message="Please add me to chores"),
        current_user=applicant,
        db=mock_db
    )
    assert created_req.data.status == "PENDING"

    # 2. Admin reviews and APPROVES join request
    ctx = HomeContext(home_id=home_id, user=owner, role="OWNER")
    mock_redis = AsyncMock()

    approved_res = await review_join_request(
        request_id=req_id,
        payload=ReviewJoinRequestInput(action="APPROVE", role="MEMBER"),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert approved_res.data.status == "APPROVED"
    assert join_req.status == "APPROVED"

    # Verify new active member and notification created
    new_members = [x for x in db_added if isinstance(x, HomeMemberModel)]
    assert len(new_members) >= 1
    assert new_members[0].user_id == applicant_id
    assert new_members[0].status == "ACTIVE"

    notifs = [x for x in db_added if isinstance(x, NotificationModel)]
    assert any(n.type == "JOIN_REQUEST_APPROVED" for n in notifs)


# ==============================================================================
# 3. INVITATION LIFECYCLE & IDENTITY BINDING
# ==============================================================================

@pytest.mark.asyncio
async def test_invitation_creation_and_email_mobile_binding():
    """Verifies invitation creation, code generation (OZ-XXXXXX), and identity checks."""
    user_id = uuid4()
    home_id = uuid4()
    user = UserModel(id=user_id, email="inviter@ozhzo.com", is_active=True)
    home = HomeModel(id=home_id, name="Sunset Villa", created_by=user_id, status="ACTIVE")

    db_added = []
    mock_db = AsyncMock()
    mock_db.get.return_value = home

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        res.scalars.return_value.first.return_value = None
        res.scalar_one_or_none.return_value = None
        return res

    mock_db.execute.side_effect = mock_exec
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))

    ctx = HomeContext(home_id=home_id, user=user, role="OWNER")
    mock_redis = AsyncMock()

    # Create invitation for a specific email
    invite_res = await create_invitation(
        payload=CreateInvitationRequest(
            email="brother@family.com",
            role="MEMBER",
            invitation_mode="INVITE_ONLY"
        ),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    data = invite_res.data
    assert data.invitation_code.startswith("OZ-")
    assert len(data.invitation_code) == 9
    assert data.email == "brother@family.com"
    assert data.status == "PENDING"


@pytest.mark.asyncio
async def test_invitation_acceptance_single_use_and_entitlement_claim():
    """
    Verifies:
    1. Invitation acceptance activates membership.
    2. Auto-claims reserved entitlement.
    3. Single-use: Subsequent attempt to re-accept raises 400.
    """
    home_id = uuid4()
    invited_user_id = uuid4()
    inv_id = uuid4()

    invited_user = UserModel(
        id=invited_user_id,
        email="brother@family.com",
        phone_number="+15551234567",
        mobile_verified=True,
        is_active=True
    )
    home = HomeModel(id=home_id, name="Sunset Villa", created_by=uuid4(), status="ACTIVE")

    invitation = InvitationModel(
        id=inv_id,
        home_id=home_id,
        email="brother@family.com",
        role="MEMBER",
        token="valid_invite_tok_101",
        invitation_code="OZ-TEST01",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc)
    )

    # Reservation for this user
    reservation = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        status="RESERVED",
        reserved_identifier_type="EMAIL",
        reserved_identifier_value="brother@family.com",
        starts_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(days=365)
    )

    db_added = []
    mock_db = AsyncMock()

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM invitations" in stmt_str:
            res.first.return_value = (invitation, home)
            res.scalar_one_or_none.return_value = invitation
        elif "FROM home_members" in stmt_str:
            res.scalar_one_or_none.return_value = None
        elif "FROM home_access_entitlements" in stmt_str:
            res.scalars.return_value.first.return_value = reservation
            res.first.return_value = (reservation,)
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.first.return_value = None
        return res

    mock_db.execute.side_effect = mock_exec
    mock_db.add = MagicMock(side_effect=lambda x: db_added.append(x))
    mock_redis = AsyncMock()

    # 1. Accept Invitation
    accept_res = await _execute_join_invitation(
        token_or_code="OZ-TEST01",
        current_user=invited_user,
        db=mock_db,
        redis_client=mock_redis
    )

    assert accept_res.home_id == home_id
    assert invitation.status == "ACCEPTED"
    assert reservation.status == "ACTIVE"
    assert reservation.user_id == invited_user_id

    # 2. Single-use guard: Trying to re-accept the same invitation raises 400
    with pytest.raises(HTTPException) as exc_info:
        await _execute_join_invitation(
            token_or_code="OZ-TEST01",
            current_user=invited_user,
            db=mock_db,
            redis_client=mock_redis
        )
    assert exc_info.value.status_code == 400
    assert "already been accepted" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_invitation_decline_flow():
    """Verifies that declining an invitation transitions its status to DECLINED."""
    user = UserModel(id=uuid4(), email="invited@ozhzo.com", is_active=True)
    inv = InvitationModel(
        id=uuid4(),
        home_id=uuid4(),
        token="tok_decline_44",
        invitation_code="OZ-DECL01",
        status="PENDING"
    )

    mock_db = AsyncMock()
    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = inv
    mock_db.execute.return_value = res_mock

    res = await decline_invitation(token_or_code="OZ-DECL01", current_user=user, db=mock_db)
    assert inv.status == "DECLINED"
    assert "declined" in res.data.message.lower()


# ==============================================================================
# 4. MEMBER LIFECYCLE: REMOVE, LEAVE, REJOIN, ROLE CHANGE
# ==============================================================================

@pytest.mark.asyncio
async def test_member_removal_and_owner_protection():
    """Verifies that workspace Owner cannot be removed, while regular members transition to REMOVED."""
    owner_id = uuid4()
    member_id = uuid4()
    home_id = uuid4()

    owner_user = UserModel(id=owner_id, email="owner@ozhzo.com", is_active=True)
    owner_member = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=owner_id, role="OWNER", status="ACTIVE")
    reg_member = HomeMemberModel(id=member_id, home_id=home_id, user_id=uuid4(), role="MEMBER", status="ACTIVE")

    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=owner_user, role="OWNER")

    # 1. Attempting to remove Owner raises 400
    res_owner_mock = MagicMock()
    res_owner_mock.scalar_one_or_none.return_value = owner_member
    mock_db.execute.return_value = res_owner_mock

    with pytest.raises(HTTPException) as exc_info:
        await remove_home_member(member_id=owner_member.id, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "cannot remove the home workspace owner" in exc_info.value.detail.lower()

    # 2. Removing regular member succeeds and transitions status to REMOVED
    res_reg_mock = MagicMock()
    res_reg_mock.scalar_one_or_none.return_value = reg_member
    mock_db.execute.return_value = res_reg_mock

    res = await remove_home_member(member_id=reg_member.id, home_ctx=ctx, db=mock_db, redis_client=mock_redis)
    assert reg_member.status == "REMOVED"
    assert "removed" in res.data.message.lower()


@pytest.mark.asyncio
async def test_member_voluntary_leave_and_owner_protection():
    """Verifies that Owner cannot leave without transfer, while members can leave voluntarily."""
    owner_id = uuid4()
    member_id = uuid4()
    home_id = uuid4()

    owner_user = UserModel(id=owner_id, email="owner@ozhzo.com", is_active=True)
    reg_user = UserModel(id=member_id, email="member@ozhzo.com", is_active=True)
    reg_member = HomeMemberModel(id=uuid4(), home_id=home_id, user_id=member_id, role="MEMBER", status="ACTIVE")

    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    # 1. Owner trying to leave raises 400
    owner_ctx = HomeContext(home_id=home_id, user=owner_user, role="OWNER")
    with pytest.raises(HTTPException) as exc_info:
        await leave_home_workspace(home_ctx=owner_ctx, db=mock_db, redis_client=mock_redis)
    assert exc_info.value.status_code == 400
    assert "owner cannot leave" in exc_info.value.detail.lower()

    # 2. Regular member leaves voluntarily -> status transitions to LEFT
    member_ctx = HomeContext(home_id=home_id, user=reg_user, role="MEMBER")
    res_reg_mock = MagicMock()
    res_reg_mock.scalar_one_or_none.return_value = reg_member
    mock_db.execute.return_value = res_reg_mock

    leave_res = await leave_home_workspace(home_ctx=member_ctx, db=mock_db, redis_client=mock_redis)
    assert reg_member.status == "LEFT"
    assert "successfully left" in leave_res.data.message.lower()


@pytest.mark.asyncio
async def test_member_rejoining_reactivates_membership():
    """Verifies that a previously REMOVED or LEFT member can rejoin cleanly without duplicate key violation."""
    user_id = uuid4()
    home_id = uuid4()

    user = UserModel(id=user_id, email="rejoiner@family.com", is_active=True)
    home = HomeModel(id=home_id, name="Harbor House", created_by=uuid4(), status="ACTIVE")

    # Existing membership record marked as REMOVED
    past_membership = HomeMemberModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        role="MEMBER",
        status="REMOVED"
    )

    invitation = InvitationModel(
        id=uuid4(),
        home_id=home_id,
        email="rejoiner@family.com",
        role="HOME_ADMIN",
        token="tok_rejoin_888",
        invitation_code="OZ-REJN01",
        status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        created_at=datetime.now(timezone.utc)
    )

    mock_db = AsyncMock()

    def mock_exec(stmt, *args, **kwargs):
        res = MagicMock()
        stmt_str = str(stmt)
        if "FROM invitations" in stmt_str:
            res.first.return_value = (invitation, home)
        elif "FROM home_members" in stmt_str:
            res.scalar_one_or_none.return_value = past_membership
        else:
            res.scalar_one_or_none.return_value = None
            res.scalars.return_value.first.return_value = None
        return res

    mock_db.execute.side_effect = mock_exec
    mock_redis = AsyncMock()

    res = await _execute_join_invitation(
        token_or_code="OZ-REJN01",
        current_user=user,
        db=mock_db,
        redis_client=mock_redis
    )

    assert res.home_id == home_id
    assert past_membership.status == "ACTIVE"
    assert past_membership.role == "HOME_ADMIN"
    assert invitation.status == "ACCEPTED"


@pytest.mark.asyncio
async def test_member_role_update_and_cache_invalidation():
    """Verifies that member role update enforces permissions and invalidates cache."""
    owner_id = uuid4()
    member_id = uuid4()
    home_id = uuid4()

    owner_user = UserModel(id=owner_id, is_active=True)
    target_member = HomeMemberModel(
        id=member_id,
        home_id=home_id,
        user_id=uuid4(),
        role="MEMBER",
        status="ACTIVE"
    )

    mock_db = AsyncMock()
    res_mem_mock = MagicMock()
    res_mem_mock.scalar_one_or_none.return_value = target_member
    mock_db.execute.return_value = res_mem_mock
    mock_redis = AsyncMock()

    ctx = HomeContext(home_id=home_id, user=owner_user, role="OWNER")
    res = await update_member_role(
        member_id=member_id,
        payload=UpdateMemberRoleRequest(role="HOME_ADMIN"),
        home_ctx=ctx,
        db=mock_db,
        redis_client=mock_redis
    )

    assert target_member.role == "HOME_ADMIN"
    assert "HOME_ADMIN" in res.data.message
    assert mock_redis.delete.called


# ==============================================================================
# 5. COMPLETE ACCESS EQUATION INVARIANT
# ==============================================================================

@pytest.mark.asyncio
async def test_complete_access_equation_invariant():
    """
    CRITICAL ACCESS INVARIANT:
    ACCESS = VALID USER + VALID MEMBERSHIP + VALID ENTITLEMENT
    """
    user_id = uuid4()
    home_id = uuid4()
    now = datetime.now(timezone.utc)

    user = UserModel(id=user_id, email="tenant@ozhzo.com", is_active=True)
    home = HomeModel(id=home_id, name="Pine Villa", created_by=uuid4(), created_at=now - timedelta(days=500), status="ACTIVE")

    # 1. User without entitlement -> Access Denied
    mock_db = AsyncMock()
    res_empty = MagicMock()
    res_empty.scalars.return_value.all.return_value = []
    res_empty.scalars.return_value.first.return_value = None
    res_empty.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = res_empty
    mock_db.get.return_value = home

    is_auth, ent, reason = await verify_user_home_access_entitlement(user, home_id, mock_db)
    assert is_auth is False
    assert ent is None

    # 2. User with active entitlement -> Access Granted
    active_ent = HomeAccessEntitlementModel(
        id=uuid4(),
        home_id=home_id,
        user_id=user_id,
        status="ACTIVE",
        starts_at=now,
        expires_at=now + timedelta(days=365)
    )
    res_active = MagicMock()
    res_active.scalars.return_value.all.return_value = [active_ent]
    mock_db.execute.return_value = res_active

    is_auth_active, ent_active, reason_active = await verify_user_home_access_entitlement(user, home_id, mock_db)
    assert is_auth_active is True
    assert ent_active.status == "ACTIVE"
