# Ozhzo Verse — Pilot Smoke Test Specification & Execution Log

**Document**: Pilot Smoke Test Specification  
**Application Version**: `0.1.0-pilot.1`  
**Execution Environment**: Local Integration / Staging Validation  
**Test Suite**: [`services/api/tests/test_pilot_smoke_test.py`](file:///Users/vivek/ozHzo/ozhzo_verse/services/api/tests/test_pilot_smoke_test.py)  
**Status**: 100% PASSED  

---

## 1. Complete First-Household Smoke Test Journey

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                 FIRST-HOUSEHOLD COMPLETE OPERATIONAL JOURNEY                │
├─────────────────────────────────────────────────────────────────────────────┤
│  1. Register Owner (Alex Pilot)              ──► 201 Created (JWT Issued)   │
│  2. Verify Mobile & User Profile             ──► 200 OK (Profile Active)    │
│  3. Create Home ("Rivera Pilot Household")   ──► 201 Created (HOME_ADMIN)   │
│  4. Invite Family Member (Sarah Pilot)       ──► 201 Created (MEMBER)       │
│  5. Member Accepts & Joins Home              ──► 200 OK (2 Active Members)  │
│  6. View Home Dashboard                      ──► 200 OK (Summary Rendered)  │
│  7. Create Location Hierarchy                ──► 201 Created (3-level path) │
│     (Store Room ➔ 3rd Cupboard ➔ Blue Box)                                 │
│  8. Add Consumable Inventory (Rice 5kg)      ──► 201 Created (Threshold: 3) │
│  9. Add Durable Asset (Mechanic Toolkit)     ──► 201 Created (In Blue Box)  │
│ 10. Search Home Memory ("toolkit")           ──► 200 OK (Exact Breadcrumb)  │
│ 11. Add Purchase Item (Rice 5kg)             ──► 201 Created (Priority HIGH)│
│ 12. Check Off Purchase Item                  ──► 200 OK (Purchased)         │
│ 13. Restock Inventory (+5kg)                 ──► 201 Created (New Stock 10) │
│ 14. Create Chore (Clean Water Filter)        ──► 201 Created (Assigned)     │
│ 15. Complete Chore with Notes                ──► 200 OK (Status: COMPLETED) │
│ 16. Create Utility Bill (Electricity $150)   ──► 201 Created (Status: UNPAID)│
│ 17. Record Full Bill Payment ($150)          ──► 201 Created (Status: PAID) │
│ 18. Schedule Birthday Event & RSVP           ──► 201 Created (RSVP: ACCEPTED│
│ 19. View Unified Today Schedule              ──► 200 OK (Projections Render)│
│ 20. View Attention Center                    ──► 200 OK (Ranked Alerts)     │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Step-by-Step API Request & Response Trace

### Step 1: Register Owner
- **Endpoint**: `POST /api/v1/auth/register`
- **Request Payload**:
  ```json
  {
    "email": "pilot_owner@ozhzo.com",
    "password": "PilotPassword123!",
    "full_name": "Alex Pilot"
  }
  ```
- **Response**: `201 Created` with JWT access token (`user_id: <owner_id>`).

### Step 2: Create Home Workspace
- **Endpoint**: `POST /api/v1/homes`
- **Request Payload**:
  ```json
  {
    "name": "Rivera Pilot Household",
    "currency": "USD",
    "timezone": "America/New_York"
  }
  ```
- **Response**: `201 Created` (`home_id: <home_id>`, role: `HOME_ADMIN`).

### Step 3: Invite Family Member
- **Endpoint**: `POST /api/v1/homes/{home_id}/members`
- **Request Payload**:
  ```json
  {
    "email": "pilot_member@ozhzo.com",
    "role": "MEMBER"
  }
  ```
- **Response**: `201 Created` (Member activated in home).

### Step 4: Add Hierarchical Location
- **Endpoint**: `POST /api/v1/homes/{home_id}/locations`
- **Hierarchy Created**:
  1. `Store Room` (ROOM)
  2. `3rd Cupboard` (FURNITURE, `parent_id`: Store Room)
  3. `Blue Box` (CONTAINER, `parent_id`: 3rd Cupboard)
- **Path Generated**: `Store Room ➔ 3rd Cupboard ➔ Blue Box`.

### Step 5: Add Consumable Stock & Durable Asset
- **Basmati Rice**: `POST /api/v1/homes/{home_id}/inventory/items` (`item_type: CONSUMABLE`, `quantity: 5`, `unit: kg`, `min_threshold: 3`).
- **Mechanic Precision Toolkit**: `POST /api/v1/homes/{home_id}/inventory/items` (`item_type: ASSET`, `location_id: <blue_box_id>`, `condition: EXCELLENT`).

### Step 6: Search Home Memory
- **Endpoint**: `GET /api/v1/homes/{home_id}/search?q=toolkit`
- **Result**:
  ```json
  {
    "items": [
      {
        "id": "<toolkit_id>",
        "title": "Mechanic Precision Toolkit",
        "domain": "ASSET",
        "location_path": "Store Room ➔ 3rd Cupboard ➔ Blue Box",
        "status": "AVAILABLE"
      }
    ]
  }
  ```

### Step 7: Purchase List Loop $\rightarrow$ Inventory Restock
1. `POST /api/v1/homes/{home_id}/purchase-list/items` $\rightarrow$ Added Basmati Rice (5 kg).
2. `PATCH /api/v1/homes/{home_id}/purchase-list/items/{id}` $\rightarrow$ `is_checked: true`.
3. `POST /api/v1/homes/{home_id}/inventory/items/{id}/movements` $\rightarrow$ `movement_type: RESTOCK`, `quantity: 5` $\rightarrow$ New balance: **10 kg**.

### Step 8: Household Task Loop
1. `POST /api/v1/homes/{home_id}/tasks` $\rightarrow$ *"Clean Water Filter Cartridge"*, assigned to Sarah Pilot.
2. `POST /api/v1/homes/{home_id}/tasks/{id}/complete` $\rightarrow$ Status updated to `COMPLETED`, notes recorded.

### Step 9: Utility Bill Payment Loop
1. `POST /api/v1/homes/{home_id}/bills` $\rightarrow$ *"City Electricity Utility"*, expected amount: `$150.00`.
2. `POST /api/v1/homes/{home_id}/bills/{id}/payments` $\rightarrow$ Amount paid: `$150.00` $\rightarrow$ Status: `PAID`, remaining balance: `$0.00`.

### Step 10: Family Calendar Event & RSVP
1. `POST /api/v1/homes/{home_id}/events` $\rightarrow$ *"Grandmother's 80th Birthday Celebration"*, participant: Sarah Pilot.
2. `POST /api/v1/homes/{home_id}/events/{id}/participants/{user_id}/status` $\rightarrow$ `status: ACCEPTED`.

### Step 11: Unified Today View & Attention Center Projections
- `GET /api/v1/homes/{home_id}/today` $\rightarrow$ Dynamic temporal schedule projecting today's birthday event, completed chore, and paid utility bill.
- `GET /api/v1/homes/{home_id}/attention` $\rightarrow$ Ranked operational alerts. Zero phantom synchronization rows created.

---

## 3. Critical Security & Isolation Tests

| Test Vector | Attack / Manipulation Tested | Expected Result | Status |
|---|---|---|---|
| **Cross-Home Dashboard** | External User X requests `GET /homes/{home_id}/dashboard` | `403 Forbidden` | **PASS** |
| **Cross-Home Today View** | External User X requests `GET /homes/{home_id}/today` | `403 Forbidden` | **PASS** |
| **Cross-Home Search Leakage** | External User X searches for *"Mechanic Precision Toolkit"* | Returns `0 items` (No cross-home leakage) | **PASS** |
| **Cross-Home IDOR Borrowing** | External User X attempts to borrow Home A's asset | `403 Forbidden` | **PASS** |
| **home_id Path Tampering** | User submits path `home_id` differing from active membership | `403 Forbidden` | **PASS** |
| **Payment Attribution** | Server assigns payer from session user token, ignoring body tampering | Payer strictly bound to authenticated user | **PASS** |
| **Asset Loan Attribution** | Server assigns lender from session user token | Lender strictly bound to authenticated user | **PASS** |

---

## 4. Verification Evidence & Quality Gates Output

```bash
$ pytest services/api/tests/test_pilot_smoke_test.py
============================== 1 passed in 0.42s ===============================
```
