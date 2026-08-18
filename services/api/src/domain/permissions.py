from typing import Dict, Set

# Role Persona definitions
ROLE_OWNER = "OWNER"
ROLE_HOME_ADMIN = "HOME_ADMIN"
ROLE_ADMIN = "ADMIN"
ROLE_MEMBER = "MEMBER"
ROLE_CHILD = "CHILD"
ROLE_GUEST = "GUEST"

# Permission Matrix Definition matching docs/PERMISSION_MODEL.md & docs/USER_ROLES.md
ROLE_PERMISSIONS_MAP: Dict[str, Set[str]] = {
    ROLE_HOME_ADMIN: {
        "home:view", "home:edit", "home:delete", "home:transfer_owner",
        "members:view", "members:invite", "members:edit", "members:remove", "members:manage_roles",
        "dashboard:view",
        "inventory:view", "inventory:create", "inventory:edit", "inventory:delete",
        "shopping:view", "shopping:create", "shopping:edit", "shopping:check", "shopping:delete",
        "tasks:view", "tasks:create", "tasks:edit", "tasks:assign", "tasks:complete", "tasks:delete",
        "bills:view", "bills:create", "bills:edit", "bills:pay", "bills:delete",
        "calendar:view", "calendar:create", "calendar:edit", "calendar:rsvp", "calendar:delete",
        "subscription:view", "subscription:manage"
    },
    ROLE_OWNER: {
        "home:view", "home:edit", "home:delete", "home:transfer_owner",
        "members:view", "members:invite", "members:edit", "members:remove", "members:manage_roles",
        "dashboard:view",
        "inventory:view", "inventory:create", "inventory:edit", "inventory:delete",
        "shopping:view", "shopping:create", "shopping:edit", "shopping:check", "shopping:delete",
        "tasks:view", "tasks:create", "tasks:edit", "tasks:assign", "tasks:complete", "tasks:delete",
        "bills:view", "bills:create", "bills:edit", "bills:pay", "bills:delete",
        "calendar:view", "calendar:create", "calendar:edit", "calendar:rsvp", "calendar:delete",
        "subscription:view", "subscription:manage"
    },
    ROLE_ADMIN: {
        "home:view", "home:edit",
        "members:view", "members:invite", "members:edit", "members:remove",
        "dashboard:view",
        "inventory:view", "inventory:create", "inventory:edit", "inventory:delete",
        "shopping:view", "shopping:create", "shopping:edit", "shopping:check", "shopping:delete",
        "tasks:view", "tasks:create", "tasks:edit", "tasks:assign", "tasks:complete", "tasks:delete",
        "bills:view", "bills:create", "bills:edit", "bills:pay", "bills:delete",
        "calendar:view", "calendar:create", "calendar:edit", "calendar:rsvp", "calendar:delete",
        "subscription:view"
    },
    ROLE_MEMBER: {
        "home:view",
        "members:view",
        "dashboard:view",
        "inventory:view", "inventory:create", "inventory:edit",
        "shopping:view", "shopping:create", "shopping:edit", "shopping:check",
        "tasks:view", "tasks:create", "tasks:edit", "tasks:complete",
        "bills:view", "bills:pay",
        "calendar:view", "calendar:create", "calendar:edit", "calendar:rsvp"
    },
    ROLE_CHILD: {
        "home:view",
        "members:view",
        "dashboard:view",
        "shopping:view", "shopping:check",
        "tasks:view", "tasks:complete",
        "calendar:view", "calendar:rsvp"
    },
    ROLE_GUEST: {
        "home:view",
        "dashboard:view",
        "shopping:view", "shopping:check",
        "tasks:view", "tasks:complete",
        "calendar:view"
    }
}


def has_permission(role: str, permission: str) -> bool:
    granted_permissions = ROLE_PERMISSIONS_MAP.get(role.upper(), set())
    return permission in granted_permissions


# Platform / System Role Definitions
PLATFORM_ROLE_SUPER_ADMIN = "SUPER_ADMIN"
PLATFORM_ROLE_PLATFORM_ADMIN = "PLATFORM_ADMIN"
PLATFORM_ROLE_SUPPORT_ADMIN = "SUPPORT_ADMIN"
PLATFORM_ROLE_ANALYST = "ANALYST"
PLATFORM_ROLE_USER = "USER"

# Platform Permission Matrix Definition
PLATFORM_ROLE_PERMISSIONS_MAP: Dict[str, Set[str]] = {
    PLATFORM_ROLE_SUPER_ADMIN: {
        "admin:dashboard:view",
        "admin:users:view",
        "admin:users:edit",
        "admin:users:disable",
        "admin:homes:view",
        "admin:homes:view_details",
        "admin:homes:edit",
        "admin:subscriptions:view",
        "admin:subscriptions:manage",
        "admin:coupons:view",
        "admin:coupons:manage",
        "admin:activity:view",
    },
    PLATFORM_ROLE_PLATFORM_ADMIN: {
        "admin:dashboard:view",
        "admin:users:view",
        "admin:users:edit",
        "admin:users:disable",
        "admin:homes:view",
        "admin:homes:view_details",
        "admin:homes:edit",
        "admin:subscriptions:view",
        "admin:subscriptions:manage",
        "admin:coupons:view",
        "admin:coupons:manage",
        "admin:activity:view",
    },
    PLATFORM_ROLE_SUPPORT_ADMIN: {
        "admin:dashboard:view",
        "admin:users:view",
        "admin:homes:view",
        "admin:homes:view_details",
        "admin:activity:view",
    },
    PLATFORM_ROLE_ANALYST: {
        "admin:dashboard:view",
        "admin:users:view",
        "admin:homes:view",
        "admin:activity:view",
    },
    PLATFORM_ROLE_USER: set(),
}


def has_platform_permission(system_role: str, permission: str) -> bool:
    if not system_role:
        return False
    granted = PLATFORM_ROLE_PERMISSIONS_MAP.get(system_role.upper(), set())
    return permission in granted
