from src.domain.permissions import (
    ROLE_OWNER, ROLE_ADMIN, ROLE_MEMBER, ROLE_CHILD, ROLE_GUEST, has_permission
)


def test_owner_has_all_permissions():
    assert has_permission(ROLE_OWNER, "home:delete") is True
    assert has_permission(ROLE_OWNER, "subscription:manage") is True
    assert has_permission(ROLE_OWNER, "bills:view") is True


def test_admin_permissions():
    assert has_permission(ROLE_ADMIN, "members:invite") is True
    assert has_permission(ROLE_ADMIN, "tasks:create") is True
    assert has_permission(ROLE_ADMIN, "home:delete") is False
    assert has_permission(ROLE_ADMIN, "subscription:manage") is False


def test_member_permissions():
    assert has_permission(ROLE_MEMBER, "tasks:complete") is True
    assert has_permission(ROLE_MEMBER, "shopping:check") is True
    assert has_permission(ROLE_MEMBER, "members:invite") is False
    assert has_permission(ROLE_MEMBER, "home:edit") is False


def test_child_privacy_protections():
    assert has_permission(ROLE_CHILD, "tasks:complete") is True
    assert has_permission(ROLE_CHILD, "shopping:check") is True
    assert has_permission(ROLE_CHILD, "bills:view") is False
    assert has_permission(ROLE_CHILD, "home:view") is True


def test_guest_restrictions():
    assert has_permission(ROLE_GUEST, "tasks:complete") is True
    assert has_permission(ROLE_GUEST, "bills:view") is False
    assert has_permission(ROLE_GUEST, "inventory:edit") is False
