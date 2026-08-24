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
    initial_password = (settings.DEMO_SUPER_ADMIN_PASSWORD or "Caseno@123").strip()

    try:
        query = select(UserModel).where(UserModel.email == email)
        result = await db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            user = UserModel(
                email=email,
                password_hash=hash_password(initial_password),
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
            # Idempotent promotion: Ensure platform Super Admin flags while preserving existing password hash
            user.is_super_admin = True
            user.system_role = "SUPER_ADMIN"
            user.is_active = True

            # If account has no password hash, initialize with initial password
            if not user.password_hash:
                user.password_hash = hash_password(initial_password)
                logger.info("Initialized password hash for existing Super Admin account: %s", email)
            else:
                logger.info("Ensured platform Super Admin authorization for account: %s (password preserved)", email)

        await db.commit()
        return user
    except Exception as e:
        await db.rollback()
        logger.error("Failed to ensure Super Admin bootstrap for %s: %e", email, e)
        return None
