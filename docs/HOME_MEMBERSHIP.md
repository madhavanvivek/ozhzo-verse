# Ozhzo Verse — Home Membership & RBAC

## 1. Overview
Home Membership bridges a `User` to a `Home` entity, declaring their role, status, and permission matrix within that specific household workspace.

## 2. Membership Roles
1. **`HOME_ADMIN` / `OWNER`**:
   - Full administrative control of the Home.
   - Can invite, modify roles, remove members, edit settings, manage subscriptions, and delete the Home.
2. **`MEMBER`**:
   - Standard family member.
   - Access to view household status, chores, inventory, shopping lists, bills, and events.
3. **`CHILD`**:
   - Restricted minor profile with read/complete task capabilities.
4. **`GUEST`**:
   - Temporary visitor access.

## 3. Membership Lifecycle Statuses
- `INVITED`: Invitation sent, pending acceptance.
- `PENDING_SUBSCRIPTION`: Awaiting Home subscription activation.
- `ACTIVE`: Fully active household member.
- `SUSPENDED`: Access temporarily restricted.
- `LEFT`: Member voluntarily departed from the Home.
- `REMOVED`: Member was removed by a `HOME_ADMIN`.
