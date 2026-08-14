# Ozhzo Verse — Phase 5: Bills & Recurring Household Expenses Data Model

## 1. Relational DDL Schema

```sql
-- 1. Bill Categories (Configurable per Home)
CREATE TABLE IF NOT EXISTS bill_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_bill_categories_home_name UNIQUE (home_id, name)
);

-- 2. Bill Templates (Common Household Bills Catalog)
CREATE TABLE IF NOT EXISTS bill_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL UNIQUE,
    default_category_name VARCHAR(100) NOT NULL DEFAULT 'Utilities',
    default_recurrence_type VARCHAR(32) NOT NULL DEFAULT 'MONTHLY',
    default_interval_days INTEGER NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. Bills Table (Obligation Definitions & Active Cycle)
CREATE TABLE IF NOT EXISTS bills (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    template_id UUID NULL REFERENCES bill_templates(id) ON DELETE SET NULL,
    category_id UUID NULL REFERENCES bill_categories(id) ON DELETE SET NULL,
    title VARCHAR(160) NOT NULL,
    expected_amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    due_date DATE NOT NULL,
    recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, MONTHLY, QUARTERLY, HALF_YEARLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days INTEGER NULL,
    recurrence_strategy VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED_DATE', -- SCHEDULED_DATE, PAYMENT_DATE
    parent_recurring_bill_id UUID NULL REFERENCES bills(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'UNPAID', -- UNPAID, PARTIALLY_PAID, PAID, CANCELLED
    amount_paid NUMERIC(12, 2) NOT NULL DEFAULT 0.00,
    responsible_member_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    notes TEXT NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 4. Bill Payments (Immutable Financial Transaction Ledger)
CREATE TABLE IF NOT EXISTS bill_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    bill_id UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    amount_paid NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'INR',
    paid_date DATE NOT NULL,
    paid_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    payment_method VARCHAR(32) NOT NULL DEFAULT 'UPI', -- CASH, BANK_TRANSFER, UPI, CARD, ONLINE, OTHER
    receipt_url TEXT NULL,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

---

## 2. Performance & Indexing Strategy

```sql
-- Fast query by Home, Status, and Due Date
CREATE INDEX IF NOT EXISTS idx_bills_home_status_due 
ON bills (home_id, status, due_date) 
WHERE deleted_at IS NULL;

-- Fast query by Responsible Member
CREATE INDEX IF NOT EXISTS idx_bills_home_responsible 
ON bills (home_id, responsible_member_id, status) 
WHERE deleted_at IS NULL;

-- Fast Payment Ledger history by Bill and Home
CREATE INDEX IF NOT EXISTS idx_bill_payments_home_bill_date 
ON bill_payments (home_id, bill_id, paid_date DESC);
```

---

## 3. Data Dictionary

### `bills`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` | Owning Home tenant boundary (FK) |
| `template_id` | `UUID` (Nullable) | Origin template from common catalog |
| `category_id` | `UUID` (Nullable) | Category FK |
| `title` | `VARCHAR(160)` | Bill title (e.g. "Electricity Bill") |
| `expected_amount` | `NUMERIC(12, 2)` | Estimated or billed expectation |
| `currency` | `VARCHAR(3)` | ISO currency code (e.g. `INR`, `AED`, `USD`) |
| `due_date` | `DATE` | Payment due date |
| `recurrence_type` | `VARCHAR(32)` | `NONE`, `MONTHLY`, `QUARTERLY`, `HALF_YEARLY`, `YEARLY`, `CUSTOM_DAYS` |
| `recurrence_interval_days` | `INTEGER` | Custom interval in days |
| `recurrence_strategy` | `VARCHAR(32)` | `SCHEDULED_DATE` vs `PAYMENT_DATE` |
| `status` | `VARCHAR(32)` | `UNPAID`, `PARTIALLY_PAID`, `PAID`, `CANCELLED` |
| `amount_paid` | `NUMERIC(12, 2)` | Aggregated total amount paid towards this bill |
| `responsible_member_id`| `UUID` (Nullable) | Member tracking/coordinating payment |
| `version` | `INTEGER` | Concurrency lock version |

### `bill_payments`
| Field | Type | Description |
|---|---|---|
| `id` | `UUID` | Primary Key |
| `home_id` | `UUID` | Owning Home tenant boundary (FK) |
| `bill_id` | `UUID` | Associated Bill (FK) |
| `amount_paid` | `NUMERIC(12, 2)` | Actual amount paid in this transaction |
| `currency` | `VARCHAR(3)` | ISO currency code |
| `paid_date` | `DATE` | Date payment was executed |
| `paid_by` | `UUID` | Member who made the payment |
| `payment_method` | `VARCHAR(32)` | `CASH`, `BANK_TRANSFER`, `UPI`, `CARD`, `ONLINE`, `OTHER` |
| `receipt_url` | `TEXT` | Receipt/invoice attachment URL |
| `notes` | `TEXT` | Transaction reference notes |
| `created_at` | `TIMESTAMPTZ` | Timestamp of logging |
