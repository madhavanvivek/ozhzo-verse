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
