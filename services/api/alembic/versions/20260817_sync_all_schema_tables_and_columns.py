"""sync all schema tables and missing columns

Revision ID: 20260817_0001
Revises: c4d8e2f10b7a
Create Date: 2026-08-17 18:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260817_0001"
down_revision: Union[str, None] = "c4d8e2f10b7a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    # 1. Homes missing columns
    homes_cols = [col["name"] for col in inspector.get_columns("homes")] if "homes" in existing_tables else []
    if "country" not in homes_cols:
        op.add_column("homes", sa.Column("country", sa.String(8), nullable=True))
    if "state_province" not in homes_cols:
        op.add_column("homes", sa.Column("state_province", sa.String(64), nullable=True))
    if "district_city" not in homes_cols:
        op.add_column("homes", sa.Column("district_city", sa.String(64), nullable=True))
    if "postal_code" not in homes_cols:
        op.add_column("homes", sa.Column("postal_code", sa.String(32), nullable=True))
    if "status" not in homes_cols:
        op.add_column("homes", sa.Column("status", sa.String(32), nullable=False, server_default="ACTIVE"))

    # 2. Home Members missing columns
    hm_cols = [col["name"] for col in inspector.get_columns("home_members")] if "home_members" in existing_tables else []
    if "created_at" not in hm_cols:
        op.add_column("home_members", sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # 3. Inventory Categories missing columns
    ic_cols = [col["name"] for col in inspector.get_columns("inventory_categories")] if "inventory_categories" in existing_tables else []
    if "color" not in ic_cols:
        op.add_column("inventory_categories", sa.Column("color", sa.String(20), nullable=True))
    if "updated_at" not in ic_cols:
        op.add_column("inventory_categories", sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))

    # 4. Invitations table
    if "invitations" not in existing_tables:
        op.create_table(
            "invitations",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("invited_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("phone_number", sa.String(32), nullable=True),
            sa.Column("email", sa.String(255), nullable=True),
            sa.Column("role", sa.String(32), nullable=False, server_default="MEMBER"),
            sa.Column("invitation_mode", sa.String(32), nullable=False, server_default="INVITE_ONLY"),
            sa.Column("token", sa.String(64), unique=True, nullable=False, index=True),
            sa.Column("status", sa.String(32), nullable=False, server_default="PENDING"),
            sa.Column("accepted_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # 5. Units table
    if "units" not in existing_tables:
        op.create_table(
            "units",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("name", sa.String(64), nullable=False),
            sa.Column("symbol", sa.String(32), nullable=False),
            sa.Column("measurement_type", sa.String(32), nullable=False, server_default="COUNT"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    # 6. Locations table
    if "locations" not in existing_tables:
        op.create_table(
            "locations",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("parent_id", UUID(as_uuid=True), sa.ForeignKey("locations.id", ondelete="CASCADE"), nullable=True, index=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("location_type", sa.String(32), nullable=False, server_default="ZONE"),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("icon", sa.String(50), nullable=True),
            sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("home_id", "parent_id", "name", name="uq_locations_home_parent_name"),
        )

    # 7. Notifications table
    if "notifications" not in existing_tables:
        op.create_table(
            "notifications",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("title", sa.String(160), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column("type", sa.String(64), nullable=False),
            sa.Column("is_read", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("idx_notifications_user_read", "notifications", ["user_id", "is_read", "created_at"])

    # 8. User Notification Preferences table
    if "user_notification_preferences" not in existing_tables:
        op.create_table(
            "user_notification_preferences",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True),
            sa.Column("in_app_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("push_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("email_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("sms_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("whatsapp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("task_assigned_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("bill_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("low_stock_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("event_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("home_invitation_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("system_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = inspector.get_table_names()

    if "user_notification_preferences" in existing_tables:
        op.drop_table("user_notification_preferences")
    if "notifications" in existing_tables:
        op.drop_index("idx_notifications_user_read", table_name="notifications")
        op.drop_table("notifications")
    if "locations" in existing_tables:
        op.drop_table("locations")
    if "units" in existing_tables:
        op.drop_table("units")
    if "invitations" in existing_tables:
        op.drop_table("invitations")

    if "inventory_categories" in existing_tables:
        ic_cols = [col["name"] for col in inspector.get_columns("inventory_categories")]
        if "updated_at" in ic_cols:
            op.drop_column("inventory_categories", "updated_at")
        if "color" in ic_cols:
            op.drop_column("inventory_categories", "color")

    if "home_members" in existing_tables:
        hm_cols = [col["name"] for col in inspector.get_columns("home_members")]
        if "created_at" in hm_cols:
            op.drop_column("home_members", "created_at")

    if "homes" in existing_tables:
        homes_cols = [col["name"] for col in inspector.get_columns("homes")]
        if "status" in homes_cols:
            op.drop_column("homes", "status")
        if "postal_code" in homes_cols:
            op.drop_column("homes", "postal_code")
        if "district_city" in homes_cols:
            op.drop_column("homes", "district_city")
        if "state_province" in homes_cols:
            op.drop_column("homes", "state_province")
        if "country" in homes_cols:
            op.drop_column("homes", "country")
