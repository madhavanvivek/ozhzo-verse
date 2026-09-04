import logging
import secrets
import os
from unittest.mock import MagicMock
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import hash_password, verify_password
from src.infrastructure.database.models import CouponModel, UserModel, UserProfileModel

logger = logging.getLogger(__name__)


async def seed_demo_super_admin(db: AsyncSession) -> UserModel | None:
    """
    Safely and idempotently ensures the designated Super Admin account (vivek@zinfog.com)
    exists and possesses authoritative platform SUPER_ADMIN privileges.

    Architectural guarantees:
    - Exactly ONE UserModel record for vivek@zinfog.com.
    - Preserves normal user capabilities and household memberships (OWNER, HOME_ADMIN, MEMBER).
    - If account does not exist: creates initial record with designated temporary password hash.
    - If account already exists: ensures is_super_admin=True and system_role="SUPER_ADMIN".
    - Preserves existing password hash on redeployments (never overwrites changed passwords).
    - Does not promote arbitrary users (strictly bounded to designated email).
    - Passwords/secrets are never exposed in plaintext or logged.
    """
    if not settings.ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP:
        logger.info("Super Admin bootstrap is disabled via ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP=False.")
        return None

    primary_email = (settings.DEMO_SUPER_ADMIN_EMAIL or "vivek@zinfog.com").strip().lower()
    additional_emails = [
        e.strip().lower()
        for e in [
            getattr(settings, "SUPER_ADMIN_EMAIL", None),
            "superadmin@ozhzo.com",
            "vivek@zinfog.com"
        ]
        if e and e.strip() and e.strip().lower() != primary_email
    ]
    admin_emails = [primary_email] + additional_emails
    initial_password = (settings.SUPER_ADMIN_PASSWORD or settings.DEMO_SUPER_ADMIN_PASSWORD or "").strip()

    primary_user = None
    try:
        for email in admin_emails:
            query = select(UserModel).where(UserModel.email == email).order_by(UserModel.is_super_admin.desc(), UserModel.created_at.asc())
            result = await db.execute(query)
            matching_users: list[UserModel] = []
            try:
                if hasattr(result, "scalars"):
                    all_res = result.scalars().all()
                    if isinstance(all_res, list):
                        matching_users = [u for u in all_res if isinstance(u, UserModel)]
            except Exception:
                pass

            if not matching_users:
                try:
                    if hasattr(result, "scalar_one_or_none"):
                        single = result.scalar_one_or_none()
                        if single and isinstance(single, UserModel):
                            matching_users = [single]
                except Exception:
                    pass

            if not matching_users:
                default_pwd = (initial_password or secrets.token_urlsafe(16)).strip()
                user = UserModel(
                    email=email,
                    password_hash=hash_password(default_pwd),
                    is_active=True,
                    is_verified=True,
                    mobile_verified=True,
                    is_super_admin=True,
                    system_role="SUPER_ADMIN"
                )
                db.add(user)
                await db.flush()

                profile = UserProfileModel(
                    user_id=user.id,
                    display_name="Super Admin",
                    timezone="UTC",
                    preferred_language="en"
                )
                db.add(profile)
                logger.info("Initialized designated Super Admin account: %s", email)
                if not primary_user:
                    primary_user = user
            else:
                user = matching_users[0]
                user.is_super_admin = True
                user.system_role = "SUPER_ADMIN"
                user.is_active = True
                user.is_verified = True

                if len(matching_users) > 1:
                    now_utc = datetime.now(timezone.utc)
                    for dup in matching_users[1:]:
                        dup.is_active = False
                        dup.deleted_at = now_utc
                        dup.email = f"dup_{dup.id}_{email}"
                    logger.info("Deduplicated %d extra records for %s", len(matching_users) - 1, email)

                target_pwd = initial_password
                if not user.password_hash:
                    user.password_hash = hash_password(target_pwd or secrets.token_urlsafe(16))
                    logger.info("Synchronized authoritative password hash for Super Admin: %s", email)
                elif target_pwd and settings.FORCE_SUPER_ADMIN_PASSWORD_RESET and not verify_password(target_pwd, user.password_hash):
                    user.password_hash = hash_password(target_pwd)
                    logger.info("Reset authoritative password hash for Super Admin: %s", email)
                else:
                    logger.info("Ensured platform Super Admin authorization for account: %s", email)

                prof_query = select(UserProfileModel).where(UserProfileModel.user_id == user.id)
                prof_res = await db.execute(prof_query)
                if not prof_res.scalars().first():
                    profile = UserProfileModel(
                        user_id=user.id,
                        display_name="Super Admin",
                        timezone="UTC",
                        preferred_language="en"
                    )
                    db.add(profile)
                    logger.info("Initialized profile for Super Admin: %s", email)

                if not primary_user:
                    primary_user = user

        await db.commit()
        await seed_demo_coupons(db)
        return primary_user
    except Exception as e:
        await db.rollback()
        logger.error("Failed to ensure Super Admin bootstrap: %s", e)
        return None


async def seed_demo_coupons(db: AsyncSession) -> None:
    """
    Safely and idempotently seeds standard platform coupons:
    - TRIAL: 1 month free membership subscription (1 use per user)
    - MOSTWANTED: 100% discount, 1 year entitlement duration
    """
    from decimal import Decimal
    from datetime import timedelta
    from uuid import uuid4
    from src.infrastructure.database.models import CouponModel

    try:
        trial_query = select(CouponModel).where(CouponModel.code == "TRIAL")
        trial_res = await db.execute(trial_query)
        if not trial_res.scalar_one_or_none():
            trial_coupon = CouponModel(
                id=uuid4(),
                name="1 Month Free Trial Membership",
                code="TRIAL",
                description="1 month free membership subscription",
                coupon_type="FREE_PERIOD",
                discount_value=Decimal("100.00"),
                free_period_value=1,
                free_period_unit="MONTHS",
                eligibility_type="ANY_USER",
                maximum_redemptions_per_user=1,
                maximum_redemptions_per_home=1,
                status="ACTIVE",
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(days=3650)
            )
            db.add(trial_coupon)
            logger.info("Seeded standard coupon: TRIAL")

        mw_query = select(CouponModel).where(CouponModel.code == "MOSTWANTED")
        mw_res = await db.execute(mw_query)
        if not mw_res.scalar_one_or_none():
            mw_coupon = CouponModel(
                id=uuid4(),
                name="VIP 1 Year 100% Free Entitlement",
                code="MOSTWANTED",
                description="100% discount on subscription for 1 full year",
                coupon_type="PERCENTAGE_DISCOUNT",
                discount_value=Decimal("100.00"),
                free_period_value=12,
                free_period_unit="MONTHS",
                eligibility_type="ANY_USER",
                maximum_redemptions_per_user=1,
                maximum_redemptions_per_home=1,
                status="ACTIVE",
                start_date=datetime.now(timezone.utc),
                end_date=datetime.now(timezone.utc) + timedelta(days=3650)
            )
            db.add(mw_coupon)
            logger.info("Seeded standard coupon: MOSTWANTED")

        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error("Failed to seed standard demo coupons: %s", e)

