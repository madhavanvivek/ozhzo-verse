# Ozhzo Verse — Multi-Home Subscription & Coupon Isolation (MULTI_HOME_SUBSCRIPTIONS.md)

**Document Version**: 1.0.0  
**Baseline Standard**: Independent Multi-Tenant Subscription Governance  

---

## 1. Multi-Home Subscription Isolation

In Ozhzo Verse, subscriptions, coupons, and direct grants are strictly scoped to individual `Home` entities (`home_id`):

```mermaid
flowchart TD
    USER[User Record: Alex Rivera]
    
    USER -->|Participates in| H1[Home 1: Primary Residence]
    USER -->|Participates in| H2[Home 2: Vacation Home]
    
    H1 --> S1[Subscription 1: Active via 6-Month Free Coupon KERALA6]
    H2 --> S2[Subscription 2: Standard Plan Trialing]
    
    S1 -.->|STRICT ISOLATION: Never Cross-Activates| S2
```

1. **Independent Entitlements**: Applying a coupon (or direct grant) to Home 1 activates benefits exclusively for Home 1. Home 2 remains on its own independent subscription terms.
2. **Cross-Home Protection**: A coupon redeemed in Home A cannot be used to activate or subsidize seats in Home B unless explicitly permitted by per-home redemption quotas.
