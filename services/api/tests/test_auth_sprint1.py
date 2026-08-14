import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from src.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_reset_token,
)
from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)


def test_password_security_unit():
    raw = "P@ssword1234!"
    hashed = hash_password(raw)
    assert hashed != raw
    assert verify_password(raw, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False


def test_jwt_access_and_refresh_tokens():
    user_id = str(uuid4())
    home_id = str(uuid4())

    access_tok = create_access_token(subject=user_id, active_home_id=home_id)
    refresh_tok = create_refresh_token(subject=user_id)

    access_payload = decode_token(access_tok)
    refresh_payload = decode_token(refresh_tok)

    assert access_payload["sub"] == user_id
    assert access_payload["home_id"] == home_id
    assert access_payload["type"] == "access"
    assert "jti" in access_payload

    assert refresh_payload["sub"] == user_id
    assert refresh_payload["type"] == "refresh"
    assert "jti" in refresh_payload


def test_reset_token_generation():
    tok1 = generate_reset_token()
    tok2 = generate_reset_token()
    assert isinstance(tok1, str)
    assert len(tok1) >= 32
    assert tok1 != tok2


def test_rbac_matrix_integrity():
    # Owner full access
    assert has_permission(ROLE_OWNER, "home:delete") is True
    assert has_permission(ROLE_OWNER, "subscription:manage") is True
    assert has_permission(ROLE_OWNER, "bills:view") is True
    
    # Admin access (cannot delete home or manage subscription)
    assert has_permission(ROLE_ADMIN, "members:invite") is True
    assert has_permission(ROLE_ADMIN, "tasks:create") is True
    assert has_permission(ROLE_ADMIN, "home:delete") is False
    assert has_permission(ROLE_ADMIN, "subscription:manage") is False

    # Child access (privacy protection: cannot view bills or settings)
    assert has_permission(ROLE_CHILD, "tasks:complete") is True
    assert has_permission(ROLE_CHILD, "shopping:check") is True
    assert has_permission(ROLE_CHILD, "bills:view") is False
    assert has_permission(ROLE_CHILD, "inventory:delete") is False

    # Guest access (scoped to assigned tasks and shopping)
    assert has_permission(ROLE_GUEST, "tasks:complete") is True
    assert has_permission(ROLE_GUEST, "bills:view") is False
    assert has_permission(ROLE_GUEST, "members:view") is False
