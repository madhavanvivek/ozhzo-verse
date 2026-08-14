# Ozhzo Verse — Multi-Home Architecture & Tenant Isolation

## 1. Multi-Home Topology
A single Ozhzo Verse user can belong to multiple Homes concurrently:

```
                  ┌───────────────┐
                  │     USER      │
                  └───────┬───────┘
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
   │   Home A    │ │   Home B    │ │   Home C    │
   │ (Primary)   │ │ (Vacation)  │ │ (Parents)   │
   │ HOME_ADMIN  │ │   MEMBER    │ │   MEMBER    │
   └─────────────┘ └─────────────┘ └─────────────┘
```

## 2. Active Home Context
- The client switches active Homes instantly without requiring session logout or re-authentication.
- Active context is passed via `X-Home-Id: <uuid>` or route path `/api/v1/homes/{home_id}/*`.
- The backend FastAPI dependency `require_home_permission(action)` strictly evaluates:
  1. Authenticated User Identity (`current_user.id`)
  2. Target Home ID (`home_id`)
  3. Membership existence in `home_members` table
  4. Membership status (`status == 'ACTIVE'`)
  5. Role permission matrix match
- Non-members receive `403 Forbidden` or `404 Not Found`.

## 3. Subscription Isolation
- Each Home maintains an independent subscription record (`subscriptions` table).
- Subscription tiers and coupon benefits apply strictly to the target Home and do not spill over to other Homes owned by the same user.
