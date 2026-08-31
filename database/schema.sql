-- Ozhzo Verse Database Initialization & DDL Schema
-- PostgreSQL 16+ with UUID and JSONB Extensions

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- 1. Users, Profiles & OTP Verifications
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(32) UNIQUE NULL,
    country_code VARCHAR(8) NULL,
    email VARCHAR(255) UNIQUE NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    mobile_verified BOOLEAN DEFAULT FALSE,
    is_super_admin BOOLEAN DEFAULT FALSE,
    system_role VARCHAR(32) NOT NULL DEFAULT 'USER',
    free_home_consumed BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE TABLE IF NOT EXISTS user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    display_name VARCHAR(100) NOT NULL,
    phone_number VARCHAR(50) NULL,
    country_code VARCHAR(8) NULL,
    avatar_url TEXT NULL,
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferred_language VARCHAR(10) DEFAULT 'en',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS otp_verifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number VARCHAR(32) NOT NULL,
    otp_code_hash VARCHAR(255) NOT NULL,
    purpose VARCHAR(32) NOT NULL DEFAULT 'REGISTRATION', -- REGISTRATION, LOGIN, INVITATION
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    attempts INTEGER NOT NULL DEFAULT 0,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(64) NOT NULL, -- USER, HOME, HOME_MEMBER, INVITATION, ROLE
    entity_id UUID NOT NULL,
    action VARCHAR(64) NOT NULL,
    performed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    details JSONB NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. Homes, Members & Identity / Join Requests
CREATE TABLE IF NOT EXISTS homes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    public_home_id VARCHAR(16) UNIQUE NULL,
    home_qr_token VARCHAR(128) UNIQUE NULL,
    home_qr_status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, REVOKED, DISABLED
    home_qr_version INTEGER NOT NULL DEFAULT 1,
    home_qr_created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    home_qr_revoked_at TIMESTAMP WITH TIME ZONE NULL,
    country VARCHAR(8) NULL,
    state_province VARCHAR(64) NULL,
    district_city VARCHAR(64) NULL,
    postal_code VARCHAR(32) NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    timezone VARCHAR(50) DEFAULT 'UTC',
    address TEXT NULL,
    avatar_url TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE INDEX IF NOT EXISTS ix_homes_public_home_id ON homes (public_home_id);
CREATE INDEX IF NOT EXISTS ix_homes_home_qr_token ON homes (home_qr_token);

CREATE TABLE IF NOT EXISTS home_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role VARCHAR(32) NOT NULL DEFAULT 'MEMBER', -- HOME_ADMIN, MEMBER
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- INVITED, PENDING_SUBSCRIPTION, ACTIVE, SUSPENDED, LEFT, REMOVED
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_home_members_home_user UNIQUE (home_id, user_id)
);

CREATE TABLE IF NOT EXISTS home_join_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, APPROVED, REJECTED, CANCELLED
    message TEXT NULL,
    reviewed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_join_requests_home_status ON home_join_requests (home_id, status);
CREATE INDEX IF NOT EXISTS idx_join_requests_user_status ON home_join_requests (user_id, status);
CREATE INDEX IF NOT EXISTS idx_join_requests_home_user_status ON home_join_requests (home_id, user_id, status);

CREATE TABLE IF NOT EXISTS invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    invited_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    phone_number VARCHAR(32) NULL,
    email VARCHAR(255) NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'MEMBER', -- HOME_ADMIN, MEMBER
    invitation_mode VARCHAR(32) NOT NULL DEFAULT 'INVITE_ONLY', -- INVITE_ONLY, INVITE_WITH_SUBSCRIPTION
    token VARCHAR(64) UNIQUE NOT NULL,
    invitation_code VARCHAR(32) UNIQUE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, ACCEPTED, REVOKED, EXPIRED, DECLINED
    accepted_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    accepted_at TIMESTAMP WITH TIME ZONE NULL,
    revoked_at TIMESTAMP WITH TIME ZONE NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_invitations_invitation_code ON invitations (invitation_code);

-- 3. Household Inventory & Home Assets
CREATE TABLE IF NOT EXISTS inventory_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL UNIQUE,
    default_category_name VARCHAR(100) NOT NULL DEFAULT 'Pantry',
    default_unit VARCHAR(32) NOT NULL DEFAULT 'kg',
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS units (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NULL REFERENCES homes(id) ON DELETE CASCADE, -- NULL = Global default, Non-NULL = Home custom
    name VARCHAR(64) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    measurement_type VARCHAR(32) NOT NULL DEFAULT 'COUNT', -- WEIGHT, VOLUME, COUNT, LENGTH, OTHER
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS inventory_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inventory_categories_home_name UNIQUE (home_id, name)
);

CREATE TABLE IF NOT EXISTS locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    parent_id UUID NULL REFERENCES locations(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    location_type VARCHAR(32) NOT NULL DEFAULT 'ZONE', -- ROOM, ZONE, FURNITURE, CONTAINER, SHELF, HOOK, VEHICLE, OTHER
    description TEXT NULL,
    icon VARCHAR(50) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT uq_locations_home_parent_name UNIQUE (home_id, parent_id, name)
);

CREATE TABLE IF NOT EXISTS inventory_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    template_id UUID NULL REFERENCES inventory_templates(id) ON DELETE SET NULL,
    category_id UUID NULL REFERENCES inventory_categories(id) ON DELETE SET NULL,
    location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    item_type VARCHAR(32) NOT NULL DEFAULT 'CONSUMABLE', -- CONSUMABLE, ASSET
    name VARCHAR(150) NOT NULL,
    description TEXT NULL,
    quantity NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    min_threshold NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    preferred_quantity NUMERIC(10, 3) NULL,
    max_quantity NUMERIC(10, 3) NULL,
    location_path TEXT NULL, -- e.g. "Store Room > 3rd Cupboard > Blue Box"
    condition VARCHAR(32) NULL, -- NEW, EXCELLENT, GOOD, FAIR, POOR, DAMAGED
    asset_status VARCHAR(32) NOT NULL DEFAULT 'AVAILABLE', -- AVAILABLE, BORROWED, MISSING, ARCHIVED
    current_holder_name VARCHAR(120) NULL,
    current_holder_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    last_seen_at TIMESTAMP WITH TIME ZONE NULL,
    last_seen_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    last_seen_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    expiry_date DATE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'GOOD', -- GOOD, LOW, OUT_OF_STOCK
    expiry_status VARCHAR(32) NOT NULL DEFAULT 'NORMAL', -- NORMAL, EXPIRING_SOON, EXPIRED
    notes TEXT NULL,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE TABLE IF NOT EXISTS stock_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    movement_type VARCHAR(32) NOT NULL, -- ADD, CONSUME, ADJUST, PURCHASE, WASTE, RETURN
    quantity_delta NUMERIC(10, 3) NOT NULL,
    previous_quantity NUMERIC(10, 3) NOT NULL,
    resulting_quantity NUMERIC(10, 3) NOT NULL,
    reason TEXT NULL,
    performed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS location_movements (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    item_id UUID NOT NULL REFERENCES inventory_items(id) ON DELETE CASCADE,
    from_location_id UUID NULL REFERENCES locations(id) ON DELETE SET NULL,
    to_location_id UUID NOT NULL REFERENCES locations(id) ON DELETE RESTRICT,
    from_location_path TEXT NULL,
    to_location_path TEXT NOT NULL,
    reason TEXT NULL,
    moved_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    moved_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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

-- 4. Home Purchase List & History
CREATE TABLE IF NOT EXISTS purchase_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    inventory_item_id UUID NULL REFERENCES inventory_items(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL DEFAULT 1.000,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    notes TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING', -- PENDING, PURCHASED, CANCELLED
    added_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_at TIMESTAMP WITH TIME ZONE NULL,
    restocked_to_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

CREATE TABLE IF NOT EXISTS purchase_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    purchase_item_id UUID NULL REFERENCES purchase_items(id) ON DELETE SET NULL,
    inventory_item_id UUID NULL REFERENCES inventory_items(id) ON DELETE SET NULL,
    stock_movement_id UUID NULL REFERENCES stock_movements(id) ON DELETE SET NULL,
    name VARCHAR(150) NOT NULL,
    quantity NUMERIC(10, 3) NOT NULL,
    unit VARCHAR(32) NOT NULL DEFAULT 'pcs',
    purchased_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    purchased_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    restocked_to_inventory BOOLEAN NOT NULL DEFAULT FALSE,
    notes TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. Tasks & Household Responsibilities
CREATE TABLE IF NOT EXISTS task_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_task_categories_home_name UNIQUE (home_id, name)
);

CREATE TABLE IF NOT EXISTS task_templates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(150) NOT NULL UNIQUE,
    default_category_name VARCHAR(100) NOT NULL DEFAULT 'Maintenance',
    default_priority VARCHAR(16) NOT NULL DEFAULT 'NORMAL',
    default_recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    default_interval_days INTEGER NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    template_id UUID NULL REFERENCES task_templates(id) ON DELETE SET NULL,
    category_id UUID NULL REFERENCES task_categories(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    priority VARCHAR(16) NOT NULL DEFAULT 'NORMAL', -- LOW, NORMAL, HIGH, URGENT
    status VARCHAR(32) NOT NULL DEFAULT 'TODO', -- TODO, IN_PROGRESS, COMPLETED, CANCELLED
    due_date TIMESTAMP WITH TIME ZONE NULL,
    recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days INTEGER NULL,
    recurrence_strategy VARCHAR(32) NOT NULL DEFAULT 'SCHEDULED_DATE', -- SCHEDULED_DATE, COMPLETION_DATE
    parent_recurring_task_id UUID NULL REFERENCES tasks(id) ON DELETE SET NULL,
    assigned_to UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    completed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    completed_at TIMESTAMP WITH TIME ZONE NULL,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL
);

-- 6. Bills & Recurring Household Expenses
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

CREATE TABLE IF NOT EXISTS bill_reminders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    bill_id UUID NOT NULL REFERENCES bills(id) ON DELETE CASCADE,
    reminder_date DATE NOT NULL,
    is_sent BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 7. Calendar & Household Events
CREATE TABLE IF NOT EXISTS event_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    icon VARCHAR(50) NULL,
    color VARCHAR(20) NULL,
    sort_order INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_event_categories_home_name UNIQUE (home_id, name)
);

CREATE TABLE IF NOT EXISTS events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    category_id UUID NULL REFERENCES event_categories(id) ON DELETE SET NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT NULL,
    location VARCHAR(255) NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_all_day BOOLEAN NOT NULL DEFAULT FALSE,
    recurrence_type VARCHAR(32) NOT NULL DEFAULT 'NONE', -- NONE, DAILY, WEEKLY, MONTHLY, YEARLY, CUSTOM_DAYS
    recurrence_interval_days INTEGER NULL,
    parent_recurring_event_id UUID NULL REFERENCES events(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'CONFIRMED', -- CONFIRMED, TENTATIVE, CANCELLED
    reminder_minutes_before INTEGER NULL DEFAULT 30,
    version INTEGER NOT NULL DEFAULT 1,
    created_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE NULL,
    CONSTRAINT chk_event_time_order CHECK (end_time >= start_time)
);

CREATE TABLE IF NOT EXISTS event_participants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) NOT NULL DEFAULT 'INVITED', -- INVITED, ACCEPTED, DECLINED
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_event_participants UNIQUE (event_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_home_timerange ON events(home_id, start_time, end_time) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_events_home_parent ON events(home_id, parent_recurring_event_id) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_event_participants_user ON event_participants(user_id, event_id);

-- 8. Notifications & Preferences
CREATE TABLE IF NOT EXISTS notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    body TEXT NOT NULL,
    data JSONB NULL,
    is_read BOOLEAN DEFAULT FALSE,
    read_at TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_notification_preferences (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    in_app_enabled BOOLEAN DEFAULT TRUE,
    push_enabled BOOLEAN DEFAULT TRUE,
    email_enabled BOOLEAN DEFAULT TRUE,
    sms_enabled BOOLEAN DEFAULT FALSE,
    whatsapp_enabled BOOLEAN DEFAULT FALSE,
    task_assigned_enabled BOOLEAN DEFAULT TRUE,
    bill_reminder_enabled BOOLEAN DEFAULT TRUE,
    low_stock_enabled BOOLEAN DEFAULT TRUE,
    event_reminder_enabled BOOLEAN DEFAULT TRUE,
    home_invitation_enabled BOOLEAN DEFAULT TRUE,
    system_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 9. Dynamic Subscription & Standard Pricing Entities
CREATE TABLE IF NOT EXISTS subscription_plans (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    description TEXT NULL,
    plan_type VARCHAR(32) NOT NULL DEFAULT 'HOME',
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    included_members INTEGER NOT NULL DEFAULT 1,
    maximum_members INTEGER NULL DEFAULT 10,
    max_homes INTEGER NOT NULL DEFAULT 10,
    additional_member_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    introductory_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    introductory_duration_days INTEGER NOT NULL DEFAULT 365,
    introductory_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    updated_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS subscription_prices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
    country VARCHAR(8) NOT NULL DEFAULT 'GLOBAL',
    region VARCHAR(32) NOT NULL DEFAULT 'GLOBAL',
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    billing_period VARCHAR(32) NOT NULL DEFAULT 'ANNUAL',
    list_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    additional_member_list_price NUMERIC(10, 2) NOT NULL DEFAULT 20.00,
    base_price NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    additional_member_price NUMERIC(10, 2) NOT NULL DEFAULT 10.00,
    version INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    effective_from TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    effective_until TIMESTAMP WITH TIME ZONE NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    CONSTRAINT uq_sub_price_version UNIQUE (plan_id, country, billing_period, version)
);

CREATE TABLE IF NOT EXISTS campaigns (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    description TEXT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP WITH TIME ZONE NULL,
    budget_limit NUMERIC(12, 2) NULL,
    maximum_redemptions INTEGER NULL,
    redemptions_count INTEGER NOT NULL DEFAULT 0,
    country VARCHAR(8) NULL,
    state VARCHAR(64) NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS coupons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    campaign_id UUID NULL REFERENCES campaigns(id) ON DELETE SET NULL,
    name VARCHAR(120) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    description TEXT NULL,
    coupon_type VARCHAR(32) NOT NULL DEFAULT 'PERCENTAGE_DISCOUNT', -- PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, FREE_PERIOD
    discount_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    free_period_value INTEGER NOT NULL DEFAULT 0,
    free_period_unit VARCHAR(16) NOT NULL DEFAULT 'MONTHS', -- DAYS, MONTHS, YEARS
    eligibility_type VARCHAR(32) NOT NULL DEFAULT 'ANY_USER', -- ANY_USER, NEW_USER, EXISTING_USER, NEW_HOME, EXISTING_HOME, INVITED_USER, SPECIFIC_USER, SPECIFIC_HOME
    target_user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    target_home_id UUID NULL REFERENCES homes(id) ON DELETE SET NULL,
    country VARCHAR(8) NULL,
    state VARCHAR(64) NULL,
    district VARCHAR(64) NULL,
    postal_code VARCHAR(32) NULL,
    currency VARCHAR(3) NULL,
    applicable_plan_id UUID NULL REFERENCES subscription_plans(id) ON DELETE SET NULL,
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP WITH TIME ZONE NULL,
    maximum_total_redemptions INTEGER NULL,
    redemptions_count INTEGER NOT NULL DEFAULT 0,
    maximum_redemptions_per_user INTEGER NOT NULL DEFAULT 1,
    maximum_redemptions_per_home INTEGER NOT NULL DEFAULT 1,
    allow_stacking BOOLEAN NOT NULL DEFAULT FALSE,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    notes TEXT NULL,
    internal_reason TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS coupon_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    coupon_id UUID NOT NULL REFERENCES coupons(id) ON DELETE CASCADE,
    campaign_id UUID NULL REFERENCES campaigns(id) ON DELETE SET NULL,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    discount_amount_applied NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    free_days_granted INTEGER NOT NULL DEFAULT 0,
    redeemed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscription_grants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    grant_type VARCHAR(32) NOT NULL DEFAULT 'FREE_PERIOD', -- FREE_PERIOD, PERCENTAGE_DISCOUNT, FIXED_DISCOUNT, EXTENDED_TRIAL
    duration_value INTEGER NOT NULL DEFAULT 0,
    duration_unit VARCHAR(16) NOT NULL DEFAULT 'MONTHS', -- DAYS, MONTHS, YEARS
    discount_value NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expiry_date TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE', -- ACTIVE, EXPIRED, REVOKED
    reason TEXT NOT NULL,
    granted_by UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS promotions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(120) NOT NULL,
    code VARCHAR(64) UNIQUE NOT NULL,
    description TEXT NULL,
    discount_type VARCHAR(32) NOT NULL DEFAULT 'PERCENTAGE',
    discount_value NUMERIC(10, 2) NOT NULL DEFAULT 50.00,
    start_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    end_date TIMESTAMP WITH TIME ZONE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    currency VARCHAR(3) NULL,
    country VARCHAR(8) NULL,
    region VARCHAR(32) NULL,
    applicable_plan_id UUID NULL REFERENCES subscription_plans(id) ON DELETE SET NULL,
    new_users_only BOOLEAN NOT NULL DEFAULT FALSE,
    existing_users_allowed BOOLEAN NOT NULL DEFAULT TRUE,
    maximum_redemptions INTEGER NULL,
    redemptions_count INTEGER NOT NULL DEFAULT 0,
    maximum_redemptions_per_user INTEGER NOT NULL DEFAULT 1,
    minimum_purchase NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS promotion_redemptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    promotion_id UUID NOT NULL REFERENCES promotions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    home_id UUID NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    discount_amount_applied NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    redeemed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscription_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscription_plan_features (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE CASCADE,
    feature_id UUID NOT NULL REFERENCES subscription_features(id) ON DELETE CASCADE,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    entitlement_limit TEXT NULL,
    CONSTRAINT uq_plan_feature_mapping UNIQUE (plan_id, feature_id)
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    home_id UUID UNIQUE NOT NULL REFERENCES homes(id) ON DELETE CASCADE,
    user_id UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    price_id UUID NULL REFERENCES subscription_prices(id) ON DELETE RESTRICT,
    active_coupon_id UUID NULL REFERENCES coupons(id) ON DELETE SET NULL,
    active_grant_id UUID NULL REFERENCES subscription_grants(id) ON DELETE SET NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'TRIALING',
    introductory_period_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    introductory_period_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
    current_period_ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
    free_period_ends_at TIMESTAMP WITH TIME ZONE NULL,
    is_free_period_active BOOLEAN NOT NULL DEFAULT FALSE,
    paid_member_seats INTEGER NOT NULL DEFAULT 0,
    
    -- Historical Price Snapshot
    list_price_snapshot NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    additional_member_list_price_snapshot NUMERIC(10, 2) NOT NULL DEFAULT 20.00,
    discount_type_snapshot VARCHAR(32) NOT NULL DEFAULT 'PERCENTAGE',
    discount_value_snapshot NUMERIC(10, 2) NOT NULL DEFAULT 50.00,
    discount_amount_snapshot NUMERIC(10, 2) NOT NULL DEFAULT 10.00,
    effective_price_snapshot NUMERIC(10, 2) NOT NULL DEFAULT 10.00,
    promotion_code_snapshot VARCHAR(64) NULL,
    currency_snapshot VARCHAR(3) NOT NULL DEFAULT 'USD',
    pricing_date_snapshot TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    renewal_policy VARCHAR(32) NOT NULL DEFAULT 'KEEP_ORIGINAL_PRICE',
    
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    base_price_locked NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    additional_member_price_locked NUMERIC(10, 2) NOT NULL DEFAULT 10.00,
    cancel_at_period_end BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS payment_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    home_id UUID NULL REFERENCES homes(id) ON DELETE SET NULL,
    subscription_id UUID NULL REFERENCES subscriptions(id) ON DELETE SET NULL,
    plan_id UUID NOT NULL REFERENCES subscription_plans(id) ON DELETE RESTRICT,
    price_id UUID NULL REFERENCES subscription_prices(id) ON DELETE SET NULL,
    coupon_id UUID NULL REFERENCES coupons(id) ON DELETE SET NULL,
    amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    tax_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    final_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    provider VARCHAR(32) NOT NULL DEFAULT 'MOCK_GATEWAY',
    provider_transaction_id VARCHAR(128) NULL,
    idempotency_key VARCHAR(128) UNIQUE NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    failure_reason TEXT NULL,
    metadata_json TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subscription_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type VARCHAR(64) NOT NULL,
    entity_id UUID NOT NULL,
    action VARCHAR(32) NOT NULL,
    performed_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
    old_values TEXT NULL,
    new_values TEXT NULL,
    reason TEXT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Multi-Tenant & Pricing Compound Indexes
CREATE INDEX IF NOT EXISTS idx_inv_items_home_search ON inventory_items(home_id, name);
CREATE INDEX IF NOT EXISTS idx_shopping_items_search ON shopping_list_items(home_id, name);
CREATE INDEX IF NOT EXISTS idx_tasks_home_search ON tasks(home_id, title);
CREATE INDEX IF NOT EXISTS idx_bills_home_search ON bills(home_id, title);
CREATE INDEX IF NOT EXISTS idx_events_home_search ON events(home_id, title);
CREATE INDEX IF NOT EXISTS idx_home_members_lookup ON home_members(home_id, user_id, status);
CREATE INDEX IF NOT EXISTS idx_notifications_user_read ON notifications(user_id, is_read, created_at);
CREATE INDEX IF NOT EXISTS idx_sub_prices_lookup ON subscription_prices(plan_id, country, currency, is_active);
CREATE INDEX IF NOT EXISTS idx_promotions_code_lookup ON promotions(code, status);
CREATE INDEX IF NOT EXISTS idx_coupons_code_lookup ON coupons(code, status);
CREATE INDEX IF NOT EXISTS idx_campaigns_code_lookup ON campaigns(code, status);
CREATE INDEX IF NOT EXISTS idx_grants_home_lookup ON subscription_grants(home_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_home_status ON subscriptions(home_id, status);
CREATE INDEX IF NOT EXISTS idx_subscriptions_user_status ON subscriptions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_pay_trans_user_status ON payment_transactions(user_id, status);
CREATE INDEX IF NOT EXISTS idx_pay_trans_created ON payment_transactions(created_at);
CREATE INDEX IF NOT EXISTS idx_sub_audit_entity ON subscription_audit_logs(entity_type, entity_id, created_at);
