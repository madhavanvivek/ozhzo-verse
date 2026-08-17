"""sync inventory_items tasks bills and all remaining domain tables

Revision ID: 20260818_0001
Revises: 20260817_0001
Create Date: 2026-08-18 01:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260818_0001"
down_revision: Union[str, None] = "20260817_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. inventory_templates
    if "inventory_templates" not in existing_tables:
        op.create_table(
            "inventory_templates",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("category_name", sa.String(100), nullable=True),
            sa.Column("suggested_unit", sa.String(32), nullable=True),
            sa.Column("default_min_threshold", sa.Numeric(10, 3), nullable=True),
            sa.Column("is_system", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("inventory_templates")

    # 2. task_categories
    if "task_categories" not in existing_tables:
        op.create_table(
            "task_categories",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("task_categories")

    # 3. bill_categories
    if "bill_categories" not in existing_tables:
        op.create_table(
            "bill_categories",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("bill_categories")

    # 4. event_categories
    if "event_categories" not in existing_tables:
        op.create_table(
            "event_categories",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(80), nullable=False),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("color", sa.String(20), nullable=True),
            sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("event_categories")

    # 5. inventory_items missing columns
    if "inventory_items" in existing_tables:
        inv_cols = {col["name"] for col in inspector.get_columns("inventory_items")}
        if "template_id" not in inv_cols:
            op.add_column("inventory_items", sa.Column("template_id", UUID(as_uuid=True), sa.ForeignKey("inventory_templates.id", ondelete="SET NULL"), nullable=True))
        if "location_id" not in inv_cols:
            op.add_column("inventory_items", sa.Column("location_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True))
        if "item_type" not in inv_cols:
            op.add_column("inventory_items", sa.Column("item_type", sa.String(32), server_default="CONSUMABLE", nullable=False))
        if "description" not in inv_cols:
            op.add_column("inventory_items", sa.Column("description", sa.Text(), nullable=True))
        if "preferred_quantity" not in inv_cols:
            op.add_column("inventory_items", sa.Column("preferred_quantity", sa.Numeric(10, 3), nullable=True))
        if "max_quantity" not in inv_cols:
            op.add_column("inventory_items", sa.Column("max_quantity", sa.Numeric(10, 3), nullable=True))
        if "location_path" not in inv_cols:
            op.add_column("inventory_items", sa.Column("location_path", sa.Text(), nullable=True))
        if "condition" not in inv_cols:
            op.add_column("inventory_items", sa.Column("condition", sa.String(32), nullable=True))
        if "asset_status" not in inv_cols:
            op.add_column("inventory_items", sa.Column("asset_status", sa.String(32), server_default="AVAILABLE", nullable=False))
        if "current_holder_name" not in inv_cols:
            op.add_column("inventory_items", sa.Column("current_holder_name", sa.String(120), nullable=True))
        if "current_holder_user_id" not in inv_cols:
            op.add_column("inventory_items", sa.Column("current_holder_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
        if "last_seen_at" not in inv_cols:
            op.add_column("inventory_items", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True))
        if "last_seen_by" not in inv_cols:
            op.add_column("inventory_items", sa.Column("last_seen_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
        if "last_seen_location_id" not in inv_cols:
            op.add_column("inventory_items", sa.Column("last_seen_location_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True))
        if "expiry_status" not in inv_cols:
            op.add_column("inventory_items", sa.Column("expiry_status", sa.String(32), server_default="NORMAL", nullable=False))
        if "notes" not in inv_cols:
            op.add_column("inventory_items", sa.Column("notes", sa.Text(), nullable=True))
        if "created_by" not in inv_cols:
            op.add_column("inventory_items", sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))

    # 6. tasks missing columns
    if "tasks" in existing_tables:
        task_cols = {col["name"] for col in inspector.get_columns("tasks")}
        if "template_id" not in task_cols:
            op.add_column("tasks", sa.Column("template_id", UUID(as_uuid=True), nullable=True))
        if "category_id" not in task_cols:
            op.add_column("tasks", sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("task_categories.id", ondelete="SET NULL"), nullable=True))
        if "recurrence_type" not in task_cols:
            op.add_column("tasks", sa.Column("recurrence_type", sa.String(32), server_default="NONE", nullable=False))
        if "recurrence_interval_days" not in task_cols:
            op.add_column("tasks", sa.Column("recurrence_interval_days", sa.Integer(), nullable=True))
        if "recurrence_strategy" not in task_cols:
            op.add_column("tasks", sa.Column("recurrence_strategy", sa.String(32), server_default="SCHEDULED", nullable=False))
        if "parent_recurring_task_id" not in task_cols:
            op.add_column("tasks", sa.Column("parent_recurring_task_id", UUID(as_uuid=True), sa.ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True))
        if "completed_by" not in task_cols:
            op.add_column("tasks", sa.Column("completed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
        if "version" not in task_cols:
            op.add_column("tasks", sa.Column("version", sa.Integer(), server_default="1", nullable=False))

    # 7. bills missing columns
    if "bills" in existing_tables:
        bill_cols = {col["name"] for col in inspector.get_columns("bills")}
        if "expected_amount" not in bill_cols:
            if "amount" in bill_cols:
                op.add_column("bills", sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True))
                op.execute("UPDATE bills SET expected_amount = amount WHERE expected_amount IS NULL")
                op.alter_column("bills", "expected_amount", nullable=False)
            else:
                op.add_column("bills", sa.Column("expected_amount", sa.Numeric(12, 2), server_default="0.00", nullable=False))
        if "template_id" not in bill_cols:
            op.add_column("bills", sa.Column("template_id", UUID(as_uuid=True), nullable=True))
        if "category_id" not in bill_cols:
            op.add_column("bills", sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("bill_categories.id", ondelete="SET NULL"), nullable=True))
        if "recurrence_type" not in bill_cols:
            op.add_column("bills", sa.Column("recurrence_type", sa.String(32), server_default="NONE", nullable=False))
        if "recurrence_interval_days" not in bill_cols:
            op.add_column("bills", sa.Column("recurrence_interval_days", sa.Integer(), nullable=True))
        if "recurrence_strategy" not in bill_cols:
            op.add_column("bills", sa.Column("recurrence_strategy", sa.String(32), server_default="SCHEDULED", nullable=False))
        if "parent_recurring_bill_id" not in bill_cols:
            op.add_column("bills", sa.Column("parent_recurring_bill_id", UUID(as_uuid=True), nullable=True))
        if "amount_paid" not in bill_cols:
            op.add_column("bills", sa.Column("amount_paid", sa.Numeric(12, 2), server_default="0.00", nullable=False))
        if "responsible_member_id" not in bill_cols:
            op.add_column("bills", sa.Column("responsible_member_id", UUID(as_uuid=True), nullable=True))
        if "notes" not in bill_cols:
            op.add_column("bills", sa.Column("notes", sa.Text(), nullable=True))
        if "version" not in bill_cols:
            op.add_column("bills", sa.Column("version", sa.Integer(), server_default="1", nullable=False))
        if "created_by" not in bill_cols:
            op.add_column("bills", sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))

    # 8. events table
    if "events" not in existing_tables:
        op.create_table(
            "events",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("category_id", UUID(as_uuid=True), sa.ForeignKey("event_categories.id", ondelete="SET NULL"), nullable=True),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("location", sa.String(150), nullable=True),
            sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_all_day", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("recurrence_type", sa.String(32), server_default="NONE", nullable=False),
            sa.Column("recurrence_interval_days", sa.Integer(), nullable=True),
            sa.Column("parent_recurring_event_id", UUID(as_uuid=True), nullable=True),
            sa.Column("status", sa.String(32), server_default="CONFIRMED", nullable=False),
            sa.Column("reminder_minutes_before", sa.Integer(), nullable=True),
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_events_home_start", "events", ["home_id", "start_time"])
        existing_tables.add("events")

    # 9. shopping_lists & shopping_list_items
    if "shopping_lists" not in existing_tables:
        op.create_table(
            "shopping_lists",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("is_default", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("shopping_lists")

    if "shopping_list_items" not in existing_tables:
        op.create_table(
            "shopping_list_items",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("list_id", UUID(as_uuid=True), sa.ForeignKey("shopping_lists.id", ondelete="CASCADE"), nullable=False),
            sa.Column("inventory_item_id", UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 3), server_default="1.000", nullable=False),
            sa.Column("unit", sa.String(32), server_default="pcs", nullable=False),
            sa.Column("priority", sa.String(16), server_default="MEDIUM", nullable=False),
            sa.Column("is_checked", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("assigned_to", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("checked_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("checked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("shopping_list_items")

    # 10. purchase_items
    if "purchase_items" not in existing_tables:
        op.create_table(
            "purchase_items",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("inventory_item_id", UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 3), server_default="1.000", nullable=False),
            sa.Column("unit", sa.String(32), server_default="pcs", nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(32), server_default="PENDING", nullable=False),
            sa.Column("added_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("purchased_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("purchased_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("restocked_to_inventory", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("version", sa.Integer(), server_default="1", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("idx_purchase_items_home_status", "purchase_items", ["home_id", "status"])
        existing_tables.add("purchase_items")

    # 11. purchase_history
    if "purchase_history" not in existing_tables:
        op.create_table(
            "purchase_history",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("purchase_item_id", UUID(as_uuid=True), sa.ForeignKey("purchase_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("inventory_item_id", UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="SET NULL"), nullable=True),
            sa.Column("stock_movement_id", UUID(as_uuid=True), nullable=True),
            sa.Column("name", sa.String(150), nullable=False),
            sa.Column("quantity", sa.Numeric(10, 3), nullable=False),
            sa.Column("unit", sa.String(32), server_default="pcs", nullable=False),
            sa.Column("purchased_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("purchased_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("restocked_to_inventory", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("purchase_history")

    # 12. asset_loans
    if "asset_loans" not in existing_tables:
        op.create_table(
            "asset_loans",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("borrower_type", sa.String(32), server_default="MEMBER", nullable=False),
            sa.Column("borrower_user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("borrower_name", sa.String(120), nullable=False),
            sa.Column("borrower_contact", sa.String(100), nullable=True),
            sa.Column("loan_status", sa.String(32), server_default="ACTIVE", nullable=False),
            sa.Column("borrowed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("expected_return_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("returned_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("return_location_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("return_location_path", sa.Text(), nullable=True),
            sa.Column("issued_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("received_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("idx_asset_loans_home_status", "asset_loans", ["home_id", "loan_status"])
        existing_tables.add("asset_loans")

    # 13. location_movements
    if "location_movements" not in existing_tables:
        op.create_table(
            "location_movements",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("from_location_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="SET NULL"), nullable=True),
            sa.Column("to_location_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("from_location_path", sa.Text(), nullable=True),
            sa.Column("to_location_path", sa.Text(), nullable=False),
            sa.Column("reason", sa.Text(), nullable=True),
            sa.Column("moved_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("moved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("location_movements")

    # 14. bill_reminders
    if "bill_reminders" not in existing_tables:
        op.create_table(
            "bill_reminders",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("bill_id", UUID(as_uuid=True), sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
            sa.Column("reminder_date", sa.Date(), nullable=False),
            sa.Column("is_sent", sa.Boolean(), server_default="false", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("bill_reminders")

    # 15. bill_payments
    if "bill_payments" not in existing_tables:
        op.create_table(
            "bill_payments",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("bill_id", UUID(as_uuid=True), sa.ForeignKey("bills.id", ondelete="CASCADE"), nullable=False),
            sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False),
            sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
            sa.Column("paid_date", sa.Date(), nullable=False),
            sa.Column("paid_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("payment_method", sa.String(32), server_default="ONLINE", nullable=False),
            sa.Column("receipt_url", sa.String(512), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("bill_payments")

    # 16. stock_movements
    if "stock_movements" not in existing_tables:
        op.create_table(
            "stock_movements",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("item_id", UUID(as_uuid=True), sa.ForeignKey("inventory_items.id", ondelete="CASCADE"), nullable=False),
            sa.Column("movement_type", sa.String(32), nullable=False),
            sa.Column("quantity_delta", sa.Numeric(10, 3), nullable=False),
            sa.Column("previous_quantity", sa.Numeric(10, 3), nullable=False),
            sa.Column("resulting_quantity", sa.Numeric(10, 3), nullable=False),
            sa.Column("reason", sa.String(255), nullable=True),
            sa.Column("performed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        existing_tables.add("stock_movements")


def downgrade() -> None:
    pass
