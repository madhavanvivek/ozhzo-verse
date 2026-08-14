# Ozhzo Verse — Subscription Seats & Dynamic Member Entitlements (SUBSCRIPTION_SEATS.md)

**Document Version**: 1.0.0  
**Baseline Standard**: Dynamic Per-Seat Billing and Entitlement Allocation  

---

## 1. Member Seat Model

Ozhzo Verse calculates household subscription costs dynamically based on allocated paid member seats:

$$\text{Total Payable} = \text{Paid Member Seats} \times \text{Unit Effective Price}$$

- **Home Admin / Custodian**: Free during configurable introductory trial (e.g. 365 days free).
- **Additional Member Seats**: Dynamically calculated based on standard list price minus applicable coupon/promotional discount.
- **Seat Allocation**: Controlled by `OWNER` via `/api/v1/subscriptions/homes/{home_id}/seats`.

---

## 2. Dynamic Entitlement States

For each member in a household workspace:
1. **Free Admin Entitlement**: The home creator/admin during introductory trial (`is_free_entitled = True`).
2. **Paid Covered Seat**: Member covered by an allocated paid seat (`is_seat_covered = True`).
3. **Uncovered Seat**: Member exceeding the home's currently paid seat quota (`is_seat_covered = False`, status marked `PAST_DUE`).
