"""add home_identity_qr_and_join_requests

Revision ID: 20260831_0001
Revises: 20260818_0002
Create Date: 2026-08-31 20:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260831_0001"
down_revision: Union[str, None] = "20260818_0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add columns to homes table if missing
    if "homes" in existing_tables:
        existing_home_cols = {c["name"] for c in inspector.get_columns("homes")}
        if "public_home_id" not in existing_home_cols:
            op.add_column("homes", sa.Column("public_home_id", sa.String(16), nullable=True))
            op.create_index("ix_homes_public_home_id", "homes", ["public_home_id"], unique=True)
        if "home_qr_token" not in existing_home_cols:
            op.add_column("homes", sa.Column("home_qr_token", sa.String(128), nullable=True))
            op.create_index("ix_homes_home_qr_token", "homes", ["home_qr_token"], unique=True)
        if "home_qr_status" not in existing_home_cols:
            op.add_column("homes", sa.Column("home_qr_status", sa.String(32), server_default="ACTIVE", nullable=False))
        if "home_qr_version" not in existing_home_cols:
            op.add_column("homes", sa.Column("home_qr_version", sa.Integer(), server_default="1", nullable=False))
        if "home_qr_created_at" not in existing_home_cols:
            op.add_column("homes", sa.Column("home_qr_created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False))
        if "home_qr_revoked_at" not in existing_home_cols:
            op.add_column("homes", sa.Column("home_qr_revoked_at", sa.DateTime(timezone=True), nullable=True))

    # 2. Add columns to invitations table if missing
    if "invitations" in existing_tables:
        existing_inv_cols = {c["name"] for c in inspector.get_columns("invitations")}
        if "invitation_code" not in existing_inv_cols:
            op.add_column("invitations", sa.Column("invitation_code", sa.String(32), nullable=True))
            op.create_index("ix_invitations_invitation_code", "invitations", ["invitation_code"], unique=True)
        if "revoked_at" not in existing_inv_cols:
            op.add_column("invitations", sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True))

    # 3. Create home_join_requests table if missing
    if "home_join_requests" not in existing_tables:
        op.create_table(
            "home_join_requests",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(32), server_default="PENDING", nullable=False),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("reviewed_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("idx_join_requests_home_status", "home_join_requests", ["home_id", "status"])
        op.create_index("idx_join_requests_user_status", "home_join_requests", ["user_id", "status"])
        op.create_index("idx_join_requests_home_user_status", "home_join_requests", ["home_id", "user_id", "status"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "home_join_requests" in existing_tables:
        op.drop_table("home_join_requests")

    if "invitations" in existing_tables:
        existing_inv_cols = {c["name"] for c in inspector.get_columns("invitations")}
        if "invitation_code" in existing_inv_cols:
            op.drop_index("ix_invitations_invitation_code", table_name="invitations")
            op.drop_column("invitations", "invitation_code")
        if "revoked_at" in existing_inv_cols:
            op.drop_column("invitations", "revoked_at")

    if "homes" in existing_tables:
        existing_home_cols = {c["name"] for c in inspector.get_columns("homes")}
        for col in ["home_qr_revoked_at", "home_qr_created_at", "home_qr_version", "home_qr_status"]:
            if col in existing_home_cols:
                op.drop_column("homes", col)
        if "home_qr_token" in existing_home_cols:
            op.drop_index("ix_homes_home_qr_token", table_name="homes")
            op.drop_column("homes", "home_qr_token")
        if "public_home_id" in existing_home_cols:
            op.drop_index("ix_homes_public_home_id", table_name="homes")
            op.drop_column("homes", "public_home_id")
