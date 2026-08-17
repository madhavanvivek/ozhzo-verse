"""sync user profiles audit logs and otp verifications

Revision ID: c4d8e2f10b7a
Revises: 997597ded82e
Create Date: 2026-08-16 16:45:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "c4d8e2f10b7a"
down_revision: Union[str, None] = "997597ded82e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update user_profiles table with missing columns
    op.add_column(
        "user_profiles",
        sa.Column("country_code", sa.String(8), nullable=True),
    )
    op.add_column(
        "user_profiles",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # 2. Create audit_logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column(
            "performed_by",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])

    # 3. Create otp_verifications table
    op.create_table(
        "otp_verifications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("phone_number", sa.String(32), nullable=False),
        sa.Column("otp_code_hash", sa.String(255), nullable=False),
        sa.Column(
            "purpose",
            sa.String(32),
            nullable=False,
            server_default="REGISTRATION",
        ),
        sa.Column(
            "is_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_otp_verifications_phone_number",
        "otp_verifications",
        ["phone_number"],
    )


def downgrade() -> None:
    op.drop_index("ix_otp_verifications_phone_number", table_name="otp_verifications")
    op.drop_table("otp_verifications")

    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_entity_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_column("user_profiles", "created_at")
    op.drop_column("user_profiles", "country_code")
