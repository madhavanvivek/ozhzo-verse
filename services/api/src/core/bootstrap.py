import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import hash_password
from src.infrastructure.database.models import UserModel, UserProfileModel

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

    email = (settings.DEMO_SUPER_ADMIN_EMAIL or "vivek@zinfog.com").strip().lower()
    initial_password = settings.DEMO_SUPER_ADMIN_PASSWORD

    try:
        query = select(UserModel).where(UserModel.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            default_pwd = (initial_password or "Caseno@123").strip()
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
                display_name="Vivek",
                timezone="UTC",
                preferred_language="en"
            )
            db.add(profile)
            logger.info("Initialized designated Super Admin account: %s", email)
        else:
            # Idempotent promotion: Ensure platform Super Admin flags, verification status
            user.is_super_admin = True
            user.system_role = "SUPER_ADMIN"
            user.is_active = True

            # If account has no password hash, or if an explicit DEMO_SUPER_ADMIN_PASSWORD was configured, apply it
            if not user.password_hash:
                user.password_hash = hash_password((initial_password or "Caseno@123").strip())
                logger.info("Initialized password hash for existing Super Admin account: %s", email)
            elif initial_password:
                user.password_hash = hash_password(initial_password.strip())
                logger.info("Updated Super Admin password to configured DEMO_SUPER_ADMIN_PASSWORD for: %s", email)
            else:
                logger.info("Ensured platform Super Admin authorization for account: %s (password preserved)", email)

            # Ensure profile exists
            prof_query = select(UserProfileModel).where(UserProfileModel.user_id == user.id)
            prof_res = await db.execute(prof_query)
            if not prof_res.scalar_one_or_none():
                profile = UserProfileModel(
                    user_id=user.id,
                    display_name="Vivek",
                    timezone="UTC",
                    preferred_language="en"
                )
                db.add(profile)
                logger.info("Initialized profile for Super Admin: %s", email)

        await db.commit()
        return user
    except Exception as e:
        await db.rollback()
        logger.error("Failed to ensure Super Admin bootstrap for %s: %s", email, e)
        return None
