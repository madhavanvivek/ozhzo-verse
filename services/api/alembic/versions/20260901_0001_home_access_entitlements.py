"""add home_access_entitlements

Revision ID: 20260901_0001
Revises: 20260831_0002
Create Date: 2026-09-01 11:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260901_0001"
down_revision: Union[str, None] = "20260831_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "home_access_entitlements" not in existing_tables:
        op.create_table(
            "home_access_entitlements",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reserved_identifier_type", sa.String(16), nullable=True),
            sa.Column("reserved_identifier_value", sa.String(255), nullable=True),
            sa.Column("entitlement_type", sa.String(32), server_default="FIRST_YEAR_FREE", nullable=False),
            sa.Column("status", sa.String(32), server_default="ACTIVE", nullable=False),
            sa.Column("starts_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("idx_entitlement_home_user", "home_access_entitlements", ["home_id", "user_id", "status"])
        op.create_index("idx_entitlement_reservation", "home_access_entitlements", ["reserved_identifier_value", "status"])
        op.create_index("idx_entitlement_expiry", "home_access_entitlements", ["expires_at", "status"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "home_access_entitlements" in existing_tables:
        op.drop_table("home_access_entitlements")
