# Ozhzo Verse — Phase 3A: Inventory, Assets & Locations Test Plan

## 1. Scope & Strategy
This test plan provides comprehensive automated test coverage for:
- Consumables and stock movement tracking
- Hierarchical locations and recursive path generation
- Location movements and `last_seen` updates
- Asset borrowing, lending history, and return flows
- Multi-home tenant isolation and role permission enforcement

---

## 2. Test Suite Matrix

### 2.1 Consumables & Stock Movements
1. **Consumable Item Creation**: Precision decimal arithmetic (`Numeric(10, 3)`), units (`kg`, `L`, `pcs`).
2. **Deterministic Stock Status Transitions**: `GOOD` $\rightarrow$ `LOW_STOCK` $\rightarrow$ `OUT_OF_STOCK` $\rightarrow$ `EXPIRED`.
3. **Stock Movement Ledger**: Logging `ADD`, `CONSUME`, `ADJUST`, `WASTE` with previous and resulting quantities.

### 2.2 Hierarchical Locations & Tree Resolution
4. **Root & Nested Location Creation**: Create `Store Room` (root) and `3rd Cupboard` (child) and `Blue Box` (grandchild).
5. **Computed Location Path**: Verify materialized path `Store Room > 3rd Cupboard > Blue Box`.
6. **Location Name Uniqueness within Parent**: Rejection of duplicate sibling location names (409 Conflict).
7. **Cross-Home Location Rejection**: Assigning a location from Home B to an item in Home A returns 403.
8. **Items Inside Location Retrieval**: Querying `/locations/{id}` returns all items residing in that location.

### 2.3 Physical Relocation & History
9. **Asset Relocation**: Moving an item from Location A to Location B records previous and new paths.
10. **Last Seen Verification**: Moving or checking an item updates `last_seen_at`, `last_seen_by`, and `last_seen_location_id`.
11. **Location History Retrieval**: Chronological audit trail of all moves for an item.

### 2.4 Asset Lending & Borrowing
12. **Borrow Asset**: Borrowing an `AVAILABLE` asset transitions it to `BORROWED`, stores borrower info and expected return date.
13. **Double Borrow Prevention**: Attempting to borrow an already borrowed asset returns 400 Bad Request.
14. **Return Asset**: Returning an asset transitions it to `AVAILABLE`, clears current holder, updates return location, and logs return timestamp.
15. **Double Return Prevention**: Returning an already returned asset returns 400 Bad Request.
16. **Borrowing History Ledger**: Chronological audit of all past and active loans for an asset.

### 2.5 Security & Multi-Home Isolation
17. **Cross-Home Asset Access**: User in Home A cannot read, move, or borrow Home B assets (403 Forbidden).
18. **Unverified Mobile Rejection**: Unverified accounts cannot create or modify assets or locations.
19. **Role Permission Enforcement**: `HOME_ADMIN` and `MEMBER` permissions verified on all asset and location routes.
