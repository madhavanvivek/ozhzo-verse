# Ozhzo Verse — Asset Borrowing & Lending Ledger

## 1. Overview
Household assets (e.g. power tools, ladders, projectors, books, camping gear) are often borrowed by family members, roommates, neighbors, or friends.

Ozhzo Verse maintains permanent Home asset ownership while tracking temporary physical custody through an immutable lending ledger.

---

## 2. Core Principles
1. **Ownership Invariant**: Lending an asset never changes the Home that owns the asset (`home_id` remains unchanged).
2. **Borrower Abstraction**: Supports internal Home Members, External Contacts (name + phone), and prepared hooks for future Connected Homes.
3. **Immutable History**: Every loan transaction is preserved for auditing and dispute prevention.

---

## 3. Asset Lending Schema

```sql
CREATE TABLE IF NOT EXISTS asset_loans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    borrower_type VARCHAR(32) NOT NULL DEFAULT 'MEMBER', -- MEMBER, EXTERNAL_PERSON, CONNECTED_HOME
    borrower_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    borrower_name VARCHAR(120) NOT NULL,
    borrower_contact VARCHAR(100) NULL,
    loan_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, RETURNED, OVERDUE, LOST
    borrowed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expected_return_at TIMESTAMP WITH TIME ZONE NULL,
    returned_at TIMESTAMP WITH TIME ZONE NULL,
    return_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    return_location_path TEXT NULL,
    issued_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    received_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_asset_loans_item_time 
ON asset_loans (item_id, borrowed_at DESC);

CREATE INDEX IF NOT EXISTS idx_asset_loans_home_status 
ON asset_loans (home_id, loan_status);
```

---

## 4. Borrowing Lifecycle & State Machine

```
   ┌────────────────────────────────────────────────────────┐
   │                     [ AVAILABLE ]                      │
   └───────────────────────────┬────────────────────────────┘
                               │
                      POST /items/{id}/borrow
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                      [ BORROWED ]                      │
   │  • Current Holder: Ashraf                              │
   │  • Borrowed Date: 12 Aug 2026                          │
   │  • Expected Return: 15 Aug 2026                        │
   └─────────────┬────────────────────────────┬─────────────┘
                 │                            │
      Current Date > Expected         POST /items/{id}/return
                 │                            │
                 ▼                            │
   ┌───────────────────────────┐              │
   │        [ OVERDUE ]        │              │
   └─────────────┬─────────────┘              │
                 │ POST /items/{id}/return    │
                 └─────────────┬──────────────┘
                               │
                               ▼
   ┌────────────────────────────────────────────────────────┐
   │                     [ AVAILABLE ]                      │
   │  • Returned to: Store > 3rd Cupboard > Blue Box        │
   │  • Returned Date: 15 Aug 2026                          │
   └────────────────────────────────────────────────────────┘
```
