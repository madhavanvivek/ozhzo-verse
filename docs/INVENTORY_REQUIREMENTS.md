# Ozhzo Verse — Phase 3A: Inventory Requirements & Functional Specification

## 1. Functional Requirements

### 1.1 Category Management
- **FR-CAT-01**: Each Home must be provisioned with default pantry categories upon creation (`Pantry`, `Fridge`, `Freezer`, `Cleaning`, `Medicine`, `Other`).
- **FR-CAT-02**: `HOME_ADMIN` and `MEMBER` can create, rename, reorder, and archive categories.
- **FR-CAT-03**: Category names must be unique within the Home tenant.

### 1.2 Item Management
- **FR-ITEM-01**: Items must store `name`, optional `category_id`, `unit`, `quantity`, `min_threshold`, `preferred_quantity`, `location`, `expiry_date`, and `notes`.
- **FR-ITEM-02**: The system must support configurable unit types (`kg`, `g`, `L`, `ml`, `pcs`, `packs`, `boxes`, `bottles`, `cans`, `bundles`, `pouches`).
- **FR-ITEM-03**: Quantity values must use high-precision decimals (`Numeric(10, 3)`) to eliminate floating-point arithmetic errors.
- **FR-ITEM-04**: Items must support soft deletion (`deleted_at` timestamp) to preserve historical movement and consumption records.

### 1.3 Stock Calculation & Deterministic Status
- **FR-STK-01**: The system must deterministically calculate stock status:
  - If `expiry_date < today` $\rightarrow$ `EXPIRED`
  - Else if `quantity == 0` $\rightarrow$ `OUT_OF_STOCK`
  - Else if `quantity <= min_threshold` $\rightarrow$ `LOW_STOCK`
  - Else $\rightarrow$ `GOOD` (or `IN_STOCK`)
- **FR-STK-02**: Manual status tampering by clients must be rejected; status is strictly server-authoritative.

### 1.4 Stock Movement Tracking
- **FR-MOV-01**: Every stock quantity modification must create an immutable `stock_movements` record.
- **FR-MOV-02**: Supported movement types:
  - `ADD`: Restocking or adding newly purchased supplies.
  - `CONSUME`: Daily household usage (supports quick actions like `-1`, `-0.5`, `-custom`).
  - `ADJUST`: Physical stock count reconciliations.
  - `PURCHASE`: Restocking via completed shopping trips.
  - `WASTE`: Spoiled, broken, or expired items discarded.
  - `RETURN`: Items returned to store or refunded.
- **FR-MOV-03**: Each movement must record: `home_id`, `item_id`, `movement_type`, `quantity_delta`, `previous_quantity`, `resulting_quantity`, `reason`, `performed_by`, and `created_at`.

---

## 2. Non-Functional Requirements

### 2.1 Tenant Security & Isolation
- **NFR-SEC-01**: All endpoints must enforce `require_home_permission(...)`. Non-members receive `403 Forbidden`.
- **NFR-SEC-02**: Cross-home access attempts by altering `home_id` must be rejected immediately.
- **NFR-SEC-03**: Unverified mobile accounts must not be permitted to read or mutate inventory data.

### 2.2 Performance & Indexing
- **NFR-PERF-01**: Query response times for inventory listings must be $< 50\text{ms}$ at p95 for households with up to 2,000 items.
- **NFR-PERF-02**: Database indexes must optimize:
  - `(home_id, deleted_at, status)`
  - `(home_id, category_id, deleted_at)`
  - `(home_id, name)` for text search prefix queries.

### 2.3 Future AI & Shopping Integration Boundaries
- **NFR-FUT-01**: Data schemas must provide clean consumption timestamps to power future AI burn-rate estimations.
- **NFR-FUT-02**: Low-stock threshold triggers must emit decoupled event payloads suitable for the future Shopping List module without hard dependencies.
