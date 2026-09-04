"""add priority, action_type, action_url, action_label, dedup_key to notifications

Revision ID: 20260901_0003
Revises: 20260901_0002
Create Date: 2026-09-01 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260901_0003"
down_revision: Union[str, None] = "20260901_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "notifications" in existing_tables:
        columns = {c["name"] for c in inspector.get_columns("notifications")}

        # 1. Relax NOT NULL constraint on home_id
        try:
            op.alter_column("notifications", "home_id", existing_type=UUID(as_uuid=True), nullable=True)
        except Exception:
            pass

        # 2. Add priority column
        if "priority" not in columns:
            op.add_column(
                "notifications",
                sa.Column("priority", sa.String(32), nullable=False, server_default="NORMAL")
            )

        # 3. Add action columns
        if "action_type" not in columns:
            op.add_column(
                "notifications",
                sa.Column("action_type", sa.String(64), nullable=True)
            )
        if "action_url" not in columns:
            op.add_column(
                "notifications",
                sa.Column("action_url", sa.String(255), nullable=True)
            )
        if "action_label" not in columns:
            op.add_column(
                "notifications",
                sa.Column("action_label", sa.String(64), nullable=True)
            )

        # 4. Add dedup_key column
        if "dedup_key" not in columns:
            op.add_column(
                "notifications",
                sa.Column("dedup_key", sa.String(128), nullable=True)
            )

        # 5. Create indexes
        indexes = {i["name"] for i in inspector.get_indexes("notifications")}
        if "idx_notifications_user_prio_read" not in indexes:
            try:
                op.create_index(
                    "idx_notifications_user_prio_read",
                    "notifications",
                    ["user_id", "priority", "is_read", "created_at"]
                )
            except Exception:
                pass

        if "idx_notifications_dedup" not in indexes:
            try:
                op.create_index(
                    "idx_notifications_dedup",
                    "notifications",
                    ["dedup_key"]
                )
            except Exception:
                pass


def downgrade() -> None:
    pass
