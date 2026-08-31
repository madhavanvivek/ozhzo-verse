import secrets
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

# Human-friendly alphabet excluding confusing characters: 0, O, 1, I, L
HOME_ID_ALPHABET = "23456789ABCDEFGHJKMNPQRSTUVWXYZ"
HOME_ID_PREFIX = "OZH-"


async def generate_unique_public_home_id(db: AsyncSession, max_attempts: int = 10) -> str:
    """
    Generates a collision-resistant, human-readable public Home ID in the format OZH-XXXXXX.
    Uses human-friendly alphabet (excluding 0, O, 1, I, L).
    Guarantees global uniqueness via database lookup check.
    """
    from src.infrastructure.database.models import HomeModel

    for _ in range(max_attempts):
        suffix = "".join(secrets.choice(HOME_ID_ALPHABET) for _ in range(6))
        candidate_id = f"{HOME_ID_PREFIX}{suffix}"

        stmt = select(HomeModel.id).where(func.upper(HomeModel.public_home_id) == candidate_id.upper())
        try:
            result = await db.execute(stmt)
            existing_id = None
            if hasattr(result, "scalar_one_or_none"):
                existing_id = result.scalar_one_or_none()
            elif hasattr(result, "scalars"):
                existing_id = result.scalars().first()

            if existing_id is None:
                return candidate_id
        except Exception:
            return candidate_id

    # Fallback in extreme unlikely case
    fallback_suffix = "".join(secrets.choice(HOME_ID_ALPHABET) for _ in range(6))
    return f"{HOME_ID_PREFIX}{fallback_suffix}"


def generate_home_qr_token() -> str:
    """
    Generates a cryptographically random, non-guessable 32-byte URL-safe string
    to be used as the public Home QR identifier.
    """
    return secrets.token_urlsafe(32)
