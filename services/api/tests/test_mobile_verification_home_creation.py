import pytest
from uuid import uuid4
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from src.core.exceptions import MobileVerificationRequiredException
from src.core.otp import OTPService, normalize_phone_number
from src.infrastructure.database.models import UserModel, UserProfileModel, HomeModel, HomeMemberModel, OTPVerificationModel
from src.api.v1.homes import create_home
from src.api.v1.users import get_my_profile, send_phone_verification_otp, verify_phone_verification_otp
from src.api.dependencies import require_home_permission
from src.schemas.home import CreateHomeRequest
from src.schemas.user import SendPhoneOTPRequest, VerifyPhoneOTPRequest


@pytest.mark.asyncio
async def test_01_user_can_login_when_mobile_unverified():
    """1. User can login and profile is retrievable even when mobile_verified=false."""
    user = UserModel(
        id=uuid4(),
        email="unverified@example.com",
        phone_number="+919876543210",
        is_active=True,
        is_verified=True,
        mobile_verified=False,
        system_role="USER"
    )
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    res = await get_my_profile(current_user=user, db=mock_db)
    assert res.success is True
    assert res.data.mobile_verified is False
    assert res.data.email == "unverified@example.com"


@pytest.mark.asyncio
async def test_02_user_can_access_existing_homes_when_mobile_unverified():
    """2. User can access existing Homes even when mobile_verified=false."""
    user_id = uuid4()
    home_id = uuid4()
    user = UserModel(
        id=user_id,
        email="member@example.com",
        phone_number="+919876543210",
        is_active=True,
        mobile_verified=False,
        system_role="USER"
    )
    membership = HomeMemberModel(
        home_id=home_id,
        user_id=user_id,
        role="MEMBER",
        status="ACTIVE"
    )

    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = membership
    mock_db.execute.return_value = mock_res
    mock_redis = AsyncMock()

    dep = require_home_permission("inventory:view")
    ctx = await dep(home_id=home_id, current_user=user, db=mock_db, redis_client=mock_redis)
    assert ctx.home_id == home_id
    assert ctx.user.id == user_id


@pytest.mark.asyncio
async def test_03_user_cannot_create_home_when_mobile_unverified():
    """3. User cannot create a new Home when mobile_verified=false (HTTP 403, MOBILE_VERIFICATION_REQUIRED)."""
    user = UserModel(
        id=uuid4(),
        email="unverified@example.com",
        phone_number="+919876543210",
        is_active=True,
        mobile_verified=False,
        system_role="USER"
    )
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    payload = CreateHomeRequest(
        name="Sunset Villa",
        country="US",
        currency="USD",
        timezone="UTC"
    )

    with pytest.raises(MobileVerificationRequiredException) as exc_info:
        await create_home(payload=payload, current_user=user, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "MOBILE_VERIFICATION_REQUIRED"
    assert "Mobile number verification is required" in exc_info.value.message


@pytest.mark.asyncio
async def test_04_super_admin_cannot_bypass_mobile_verification_for_home_creation():
    """4. Super Admin status MUST NOT bypass mobile verification for normal Home creation."""
    super_admin_unverified = UserModel(
        id=uuid4(),
        email="superadmin@example.com",
        phone_number="+919876543210",
        is_active=True,
        is_super_admin=True,
        system_role="SUPER_ADMIN",
        mobile_verified=False
    )
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    payload = CreateHomeRequest(
        name="Platform HQ Home",
        country="US",
        currency="USD",
        timezone="UTC"
    )

    with pytest.raises(MobileVerificationRequiredException) as exc_info:
        await create_home(payload=payload, current_user=super_admin_unverified, db=mock_db, redis_client=mock_redis)

    assert exc_info.value.status_code == 403
    assert exc_info.value.code == "MOBILE_VERIFICATION_REQUIRED"


@pytest.mark.asyncio
async def test_05_verified_user_can_create_home():
    """5. Verified user (mobile_verified=true) can create a Home successfully."""
    user = UserModel(
        id=uuid4(),
        email="verified@example.com",
        phone_number="+919876543210",
        is_active=True,
        mobile_verified=True,
        system_role="USER"
    )
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    # No existing homes owned
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    payload = CreateHomeRequest(
        name="Sunny Heights",
        country="US",
        currency="USD",
        timezone="UTC"
    )

    res = await create_home(payload=payload, current_user=user, db=mock_db, redis_client=mock_redis)
    assert res.success is True
    assert res.data.name == "Sunny Heights"
    assert res.data.role == "HOME_ADMIN"


@pytest.mark.asyncio
async def test_06_otp_lifecycle_send_and_verify():
    """6. OTP service creates, hashes, expires previous OTPs, and verifies code successfully."""
    otp_service = OTPService()
    mock_db = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_res

    phone = "+919876543210"
    norm_phone, code = await otp_service.create_and_send_otp(mock_db, phone, purpose="PHONE_VERIFICATION")
    assert norm_phone == phone
    assert mock_db.add.called
    assert mock_db.commit.called

    # Verification
    otp_record = OTPVerificationModel(
        id=uuid4(),
        phone_number=norm_phone,
        otp_code_hash=OTPService._hash_otp(code or "123456", norm_phone),
        purpose="PHONE_VERIFICATION",
        is_verified=False,
        attempts=0,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    mock_res_verify = MagicMock()
    mock_res_verify.scalars.return_value.first.return_value = otp_record
    mock_db.execute.return_value = mock_res_verify

    verified = await otp_service.verify_otp(mock_db, norm_phone, code or "123456", purpose="PHONE_VERIFICATION")
    assert verified is True
    assert otp_record.is_verified is True


@pytest.mark.asyncio
async def test_07_otp_invalid_code_and_attempt_limits():
    """7. Invalid OTP increments attempts and locks after 5 attempts."""
    otp_service = OTPService()
    mock_db = AsyncMock()
    phone = "+919876543210"

    otp_record = OTPVerificationModel(
        id=uuid4(),
        phone_number=phone,
        otp_code_hash=OTPService._hash_otp("123456", phone),
        purpose="PHONE_VERIFICATION",
        is_verified=False,
        attempts=0,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = otp_record
    mock_db.execute.return_value = mock_res

    # 1. Wrong code fails
    with pytest.raises(HTTPException) as exc1:
        await otp_service.verify_otp(mock_db, phone, "000000", purpose="PHONE_VERIFICATION")
    assert exc1.value.status_code == 400
    assert otp_record.attempts == 1

    # 2. Exceeding 5 attempts locks with 429
    otp_record.attempts = 5
    with pytest.raises(HTTPException) as exc2:
        await otp_service.verify_otp(mock_db, phone, "123456", purpose="PHONE_VERIFICATION")
    assert exc2.value.status_code == 429
    assert "Too many invalid OTP attempts" in exc2.value.detail


@pytest.mark.asyncio
async def test_08_otp_expired_code():
    """8. Expired OTP fails verification."""
    otp_service = OTPService()
    mock_db = AsyncMock()
    phone = "+919876543210"

    otp_record = OTPVerificationModel(
        id=uuid4(),
        phone_number=phone,
        otp_code_hash=OTPService._hash_otp("123456", phone),
        purpose="PHONE_VERIFICATION",
        is_verified=False,
        attempts=0,
        expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)  # expired
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = otp_record
    mock_db.execute.return_value = mock_res

    with pytest.raises(HTTPException) as exc:
        await otp_service.verify_otp(mock_db, phone, "123456", purpose="PHONE_VERIFICATION")
    assert exc.value.status_code == 400
    assert "OTP code has expired" in exc.value.detail


@pytest.mark.asyncio
async def test_09_authenticated_phone_verification_updates_profile():
    """9. POST /users/me/phone/verify-otp marks user as mobile_verified=True and adds audit log."""
    user = UserModel(
        id=uuid4(),
        email="testuser@example.com",
        phone_number=None,
        is_active=True,
        mobile_verified=False,
        system_role="USER"
    )
    mock_db = AsyncMock()
    mock_redis = AsyncMock()

    phone = "+919876543210"
    otp_record = OTPVerificationModel(
        id=uuid4(),
        phone_number=phone,
        otp_code_hash=OTPService._hash_otp("123456", phone),
        purpose="PHONE_VERIFICATION",
        is_verified=False,
        attempts=0,
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
    )
    mock_res = MagicMock()
    mock_res.scalars.return_value.first.return_value = otp_record
    mock_res.all.return_value = []
    mock_db.execute.return_value = mock_res

    payload = VerifyPhoneOTPRequest(
        phone_number="9876543210",
        country_code="+91",
        otp_code="123456"
    )

    res = await verify_phone_verification_otp(
        payload=payload,
        current_user=user,
        db=mock_db,
        redis_client=mock_redis
    )

    assert user.mobile_verified is True
    assert user.phone_number == phone
    assert res.data.mobile_verified is True
    assert mock_db.commit.called


@pytest.mark.asyncio
async def test_10_demo_otp_enabled_generates_and_accepts_fixed_code():
    """10. When DEMO_OTP_ENABLED=True, 123456 is generated and verifies successfully."""
    from src.core.config import settings

    with patch.object(settings, "DEMO_OTP_ENABLED", True), patch.object(settings, "ENVIRONMENT", "staging"):
        otp_service = OTPService()
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_res

        phone = "+919876543210"
        norm_phone, code = await otp_service.create_and_send_otp(mock_db, phone, purpose="PHONE_VERIFICATION")
        assert code == "123456"
        assert norm_phone == phone

        # Verification with 123456
        otp_record = OTPVerificationModel(
            id=uuid4(),
            phone_number=norm_phone,
            otp_code_hash=OTPService._hash_otp("123456", norm_phone),
            purpose="PHONE_VERIFICATION",
            is_verified=False,
            attempts=0,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        mock_res_verify = MagicMock()
        mock_res_verify.scalars.return_value.first.return_value = otp_record
        mock_db.execute.return_value = mock_res_verify

        verified = await otp_service.verify_otp(mock_db, norm_phone, "123456", purpose="PHONE_VERIFICATION")
        assert verified is True
        assert otp_record.is_verified is True


@pytest.mark.asyncio
async def test_11_demo_otp_disabled_in_production_fails_fixed_code():
    """11. When DEMO_OTP_ENABLED=False and ENVIRONMENT=production, 123456 fails unless it was randomly generated."""
    from src.core.config import settings

    with patch.object(settings, "DEMO_OTP_ENABLED", False), patch.object(settings, "ENVIRONMENT", "production"):
        otp_service = OTPService()
        mock_db = AsyncMock()
        mock_res = MagicMock()
        mock_res.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_res

        phone = "+919876543210"
        with patch("secrets.randbelow", return_value=888888):  # generated code will be 888888 + 100000 = 988888
            norm_phone, dev_code = await otp_service.create_and_send_otp(mock_db, phone, purpose="PHONE_VERIFICATION")
            assert dev_code is None  # Never leaked in production

        # Stored hash is for 988888
        otp_record = OTPVerificationModel(
            id=uuid4(),
            phone_number=norm_phone,
            otp_code_hash=OTPService._hash_otp("988888", norm_phone),
            purpose="PHONE_VERIFICATION",
            is_verified=False,
            attempts=0,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10)
        )
        mock_res_verify = MagicMock()
        mock_res_verify.scalars.return_value.first.return_value = otp_record
        mock_db.execute.return_value = mock_res_verify

        # Attempting 123456 fails
        with pytest.raises(HTTPException) as exc:
            await otp_service.verify_otp(mock_db, norm_phone, "123456", purpose="PHONE_VERIFICATION")
        assert exc.value.status_code == 400
        assert "Invalid OTP verification code" in exc.value.detail
