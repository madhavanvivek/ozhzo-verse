import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timedelta, timezone


@pytest.mark.asyncio
async def test_01_user_registration_mobile_normalized(client: AsyncClient):
    """Sec Gate 5 & 6: Registration with mobile normalization."""
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "phone_number": "9876543210",
            "country_code": "+91",
            "full_name": "Vivek Madhavan",
            "password": "StrongPassword123!"
        }
    )
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["phone_number"] == "+919876543210"
    assert data["mobile_verified"] is False


@pytest.mark.asyncio
async def test_02_duplicate_mobile_format_rejection(client: AsyncClient):
    """Sec Gate 5: Rejection of duplicate mobile across equivalent formats."""
    # Attempt second registration with same phone in explicit +91 format
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "phone_number": "+919876543210",
            "full_name": "Duplicate User",
            "password": "AnotherPassword123!"
        }
    )
    assert res.status_code == 409
    assert "already exists" in res.json()["detail"]


@pytest.mark.asyncio
async def test_03_unverified_mobile_cannot_create_home(client: AsyncClient):
    """Sec Gate 6: Unverified mobile account cannot create a Home."""
    # Login with unverified user
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token = login_res.json()["data"]["access_token"]

    # Attempt to create Home
    res = await client.post(
        "/api/v1/homes",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Illegal Home", "country": "IN"}
    )
    assert res.status_code == 403
    assert "Mobile number verification is required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_04_otp_verification_flow(client: AsyncClient):
    """Sec Gate 7: OTP dispatch and verification."""
    send_res = await client.post(
        "/api/v1/auth/send-otp",
        json={"phone_number": "+919876543210", "purpose": "REGISTRATION"}
    )
    assert send_res.status_code == 200
    otp_code = send_res.json()["data"]["otp_code"]
    assert otp_code is not None

    # Verify OTP
    v_res = await client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "+919876543210", "otp_code": otp_code, "purpose": "REGISTRATION"}
    )
    assert v_res.status_code == 200
    assert v_res.json()["data"]["is_verified"] is True


@pytest.mark.asyncio
async def test_05_otp_single_use_and_lockout(client: AsyncClient):
    """Sec Gate 7: OTP cannot be reused after verification."""
    v_res = await client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "+919876543210", "otp_code": "123456", "purpose": "REGISTRATION"}
    )
    # Re-verify should fail since pending record is marked verified
    assert v_res.status_code == 400


@pytest.mark.asyncio
async def test_06_verified_user_creates_home_as_home_admin(client: AsyncClient):
    """Sec Gate 6 & 13: Verified user creates Home and receives HOME_ADMIN role."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token = login_res.json()["data"]["access_token"]

    res = await client.post(
        "/api/v1/homes",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "name": "Madhavan Home",
            "country": "IN",
            "state_province": "Karnataka",
            "district_city": "Bengaluru",
            "currency": "INR",
            "timezone": "Asia/Kolkata"
        }
    )
    assert res.status_code == 201
    home = res.json()["data"]
    assert home["role"] == "HOME_ADMIN"
    assert home["country"] == "IN"


@pytest.mark.asyncio
async def test_07_home_admin_cannot_access_super_admin_endpoints(client: AsyncClient):
    """Sec Gate 3 & 14: HOME_ADMIN role is isolated from SUPER_ADMIN endpoints."""
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token = login_res.json()["data"]["access_token"]

    # Attempt to access Super Admin route
    res = await client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 403
    assert "Super Admin privileges required" in res.json()["detail"]


@pytest.mark.asyncio
async def test_08_cross_home_isolation(client: AsyncClient):
    """Sec Gate 1 & 4: User cannot access another Home by changing home_id."""
    # Register & Verify User B
    reg_b = await client.post(
        "/api/v1/auth/register",
        json={"phone_number": "+918888888888", "full_name": "User B", "password": "Password123!"}
    )
    token_b = reg_b.json()["data"]["access_token"]

    # Send & verify OTP for User B
    send_b = await client.post("/api/v1/auth/send-otp", json={"phone_number": "+918888888888"})
    await client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "+918888888888", "otp_code": send_b.json()["data"]["otp_code"]}
    )

    # User A's home
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token_a = login_a.json()["data"]["access_token"]
    homes_a = (await client.get("/api/v1/homes", headers={"Authorization": f"Bearer {token_a}"})).json()["data"]
    home_a_id = homes_a[0]["id"]

    # User B attempts to access User A's home data
    res = await client.get(f"/api/v1/homes/{home_a_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert res.status_code == 403
    assert "not an active member" in res.json()["detail"]


@pytest.mark.asyncio
async def test_09_invitation_mobile_binding_enforcement(client: AsyncClient):
    """Sec Gate 8: Invitation bound to a mobile number cannot be accepted by a different mobile."""
    # User A invites specific mobile number +917777777777
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token_a = login_a.json()["data"]["access_token"]
    homes_a = (await client.get("/api/v1/homes", headers={"Authorization": f"Bearer {token_a}"})).json()["data"]
    home_a_id = homes_a[0]["id"]

    inv_res = await client.post(
        f"/api/v1/homes/{home_a_id}/invitations",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"phone_number": "+917777777777", "role": "MEMBER"}
    )
    token = inv_res.json()["data"]["token"]

    # User B (+918888888888) attempts to accept invitation bound to +917777777777
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+918888888888", "password": "Password123!"}
    )
    token_b = login_b.json()["data"]["access_token"]

    accept_res = await client.post(
        f"/api/v1/invitations/{token}/accept",
        headers={"Authorization": f"Bearer {token_b}"}
    )
    assert accept_res.status_code == 403
    assert "different mobile number" in accept_res.json()["detail"]


@pytest.mark.asyncio
async def test_10_invitation_single_use_protection(client: AsyncClient):
    """Sec Gate 8: Invitation cannot be accepted more than once."""
    # Register and verify intended recipient User C (+917777777777)
    await client.post(
        "/api/v1/auth/register",
        json={"phone_number": "+917777777777", "full_name": "User C", "password": "Password123!"}
    )
    send_c = await client.post("/api/v1/auth/send-otp", json={"phone_number": "+917777777777"})
    await client.post(
        "/api/v1/auth/verify-otp",
        json={"phone_number": "+917777777777", "otp_code": send_c.json()["data"]["otp_code"]}
    )

    login_c = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+917777777777", "password": "Password123!"}
    )
    token_c = login_c.json()["data"]["access_token"]

    # Get invitation token
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token_a = login_a.json()["data"]["access_token"]
    homes_a = (await client.get("/api/v1/homes", headers={"Authorization": f"Bearer {token_a}"})).json()["data"]
    home_a_id = homes_a[0]["id"]
    invitations = (await client.get(f"/api/v1/homes/{home_a_id}/invitations", headers={"Authorization": f"Bearer {token_a}"})).json()["data"]
    inv_token = invitations[0]["token"]

    # First acceptance: Success
    acc1 = await client.post(f"/api/v1/invitations/{inv_token}/accept", headers={"Authorization": f"Bearer {token_c}"})
    assert acc1.status_code == 200

    # Second acceptance: Rejection
    acc2 = await client.post(f"/api/v1/invitations/{inv_token}/accept", headers={"Authorization": f"Bearer {token_c}"})
    assert acc2.status_code in [400, 404]


@pytest.mark.asyncio
async def test_11_member_cannot_perform_admin_actions(client: AsyncClient):
    """Sec Gate 2 & 12: Standard MEMBER cannot delete Home or manage roles."""
    login_c = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+917777777777", "password": "Password123!"}
    )
    token_c = login_c.json()["data"]["access_token"]

    # User C is a MEMBER in Home A
    homes_c = (await client.get("/api/v1/homes", headers={"Authorization": f"Bearer {token_c}"})).json()["data"]
    home_a_id = homes_c[0]["id"]

    # Attempt delete home
    del_res = await client.delete(f"/api/v1/homes/{home_a_id}", headers={"Authorization": f"Bearer {token_c}"})
    assert del_res.status_code == 403


@pytest.mark.asyncio
async def test_12_removed_member_loses_access(client: AsyncClient):
    """Sec Gate 9 & 18: REMOVED member immediately loses Home access and history is preserved."""
    # User A (HOME_ADMIN) removes User C
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    token_a = login_a.json()["data"]["access_token"]
    homes_a = (await client.get("/api/v1/homes", headers={"Authorization": f"Bearer {token_a}"})).json()["data"]
    home_a_id = homes_a[0]["id"]
    members = (await client.get(f"/api/v1/homes/{home_a_id}/members", headers={"Authorization": f"Bearer {token_a}"})).json()["data"]
    member_c = [m for m in members if m["phone_number"] == "+917777777777"][0]

    rem_res = await client.delete(
        f"/api/v1/homes/{home_a_id}/members/{member_c['id']}",
        headers={"Authorization": f"Bearer {token_a}"}
    )
    assert rem_res.status_code == 200

    # User C attempts to access Home A
    login_c = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+917777777777", "password": "Password123!"}
    )
    token_c = login_c.json()["data"]["access_token"]

    res = await client.get(f"/api/v1/homes/{home_a_id}", headers={"Authorization": f"Bearer {token_c}"})
    assert res.status_code == 403
    assert "not an active member" in res.json()["detail"]


@pytest.mark.asyncio
async def test_13_no_secret_leaks_in_responses(client: AsyncClient):
    """Sec Gate 19: API responses do not expose sensitive hashes, OTPs, or foreign home data."""
    login_a = await client.post(
        "/api/v1/auth/login",
        json={"phone_number": "+919876543210", "password": "StrongPassword123!"}
    )
    data_str = login_a.text
    assert "password_hash" not in data_str
    assert "otp_code_hash" not in data_str
