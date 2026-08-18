import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.security import hash_password
from src.infrastructure.database.models import UserModel, UserProfileModel

logger = logging.getLogger(__name__)


async def seed_demo_super_admin(db: AsyncSession) -> UserModel | None:
    """
    Explicitly and idempotently seeds or designates the initial demo Super Admin.
    - Requires BOTH ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP=True AND DEMO_SUPER_ADMIN_PASSWORD=<value>.
    - If disabled or missing password, safely returns None without failing startup or creating records.
    - If account does not exist: creates record using supplied password.
    - If account already exists: preserves existing password/hash and ensures platform Super Admin flags.
    - Preserves normal user identity and household capabilities.
    - Exactly one designated account (vivek@zinfog.com).
    - Passwords/secrets are never exposed via API responses.
    """
    if not settings.ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP or not settings.DEMO_SUPER_ADMIN_PASSWORD:
        logger.info(
            "Demo Super Admin bootstrap skipped (ENABLE_DEMO_SUPER_ADMIN_BOOTSTRAP is false or password not supplied)."
        )
        return None

    email = (settings.DEMO_SUPER_ADMIN_EMAIL or "vivek@zinfog.com").strip().lower()
    password = settings.DEMO_SUPER_ADMIN_PASSWORD.strip()

    query = select(UserModel).where(UserModel.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        user = UserModel(
            email=email,
            password_hash=hash_password(password),
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
        logger.info("Created initial demo Super Admin account: %s", email)
    else:
        # Idempotency: Preserve existing user credentials and ensure platform roles
        user.is_super_admin = True
        user.system_role = "SUPER_ADMIN"
        user.is_active = True
        logger.info("Ensured platform Super Admin flags for existing user: %s (password preserved)", email)

    await db.commit()
    return user
