"""add subscription_credits ledger and credit_amount to payment_transactions

Revision ID: 20260901_0002
Revises: 20260901_0001
Create Date: 2026-09-01 11:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260901_0002"
down_revision: Union[str, None] = "20260901_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add credit_amount to payment_transactions if not present
    if "payment_transactions" in existing_tables:
        columns = {c["name"] for c in inspector.get_columns("payment_transactions")}
        if "credit_amount" not in columns:
            op.add_column(
                "payment_transactions",
                sa.Column("credit_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00")
            )

    # 2. Create subscription_credits table if not present
    if "subscription_credits" not in existing_tables:
        op.create_table(
            "subscription_credits",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("remaining_amount", sa.Numeric(10, 2), nullable=False, server_default="0.00"),
            sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
            sa.Column("credit_type", sa.String(32), nullable=False, server_default="ADMIN_GRANT"),
            sa.Column("status", sa.String(32), nullable=False, server_default="AVAILABLE"),
            sa.Column("source_type", sa.String(64), nullable=True),
            sa.Column("source_id", UUID(as_uuid=True), nullable=True),
            sa.Column("reference", sa.String(128), nullable=True),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("redeemed_transaction_id", UUID(as_uuid=True), sa.ForeignKey("payment_transactions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_by", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        )
        op.create_index("idx_sub_credits_user_status", "subscription_credits", ["user_id", "status"])
        op.create_index("idx_sub_credits_user_curr_status", "subscription_credits", ["user_id", "currency", "status"])
        op.create_index("idx_sub_credits_home_status", "subscription_credits", ["home_id", "status"])
        op.create_index("idx_sub_credits_created", "subscription_credits", ["created_at"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "subscription_credits" in existing_tables:
        op.drop_table("subscription_credits")

    if "payment_transactions" in existing_tables:
        columns = {c["name"] for c in inspector.get_columns("payment_transactions")}
        if "credit_amount" in columns:
            op.drop_column("payment_transactions", "credit_amount")
