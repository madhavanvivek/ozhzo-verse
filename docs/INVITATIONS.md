# Ozhzo Verse — Home Invitations

## 1. Overview
The Home Invitation subsystem enables `HOME_ADMIN` users to invite family members, roommates, or domestic managers via secure, cryptographically unguessable invitation tokens.

## 2. Invitation Modes
1. **`INVITE_ONLY`**:
   - Standard invitation. The recipient immediately becomes an `ACTIVE` member upon acceptance.
2. **`INVITE_WITH_SUBSCRIPTION`**:
   - Invitation requires an active Home subscription. If the Home subscription is expired or pending, the new member is placed into `PENDING_SUBSCRIPTION` status until the Home subscription is active.

## 3. Mobile Number Binding & Security
- When an invitation is created with a `phone_number`, only an authenticated user with that verified mobile number can accept the invitation.
- Reusing accepted invitation tokens is prevented (status changes to `ACCEPTED` and stores `accepted_by` / `accepted_at`).
- Expired invitations (default 7 days) are rejected automatically.
