"""add stage2_2_monetization_and_payments

Revision ID: 20260831_0002
Revises: 20260831_0001
Create Date: 2026-08-31 21:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "20260831_0002"
down_revision: Union[str, None] = "20260831_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    # 1. Add free_home_consumed to users if missing
    if "users" in existing_tables:
        existing_user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "free_home_consumed" not in existing_user_cols:
            op.add_column("users", sa.Column("free_home_consumed", sa.Boolean(), server_default="false", nullable=False))
            op.create_index("ix_users_free_home_consumed", "users", ["free_home_consumed"])

    # 2. Add max_homes to subscription_plans if missing
    if "subscription_plans" in existing_tables:
        existing_plan_cols = {c["name"] for c in inspector.get_columns("subscription_plans")}
        if "max_homes" not in existing_plan_cols:
            op.add_column("subscription_plans", sa.Column("max_homes", sa.Integer(), server_default="10", nullable=False))

    # 3. Add user_id to subscriptions if missing
    if "subscriptions" in existing_tables:
        existing_sub_cols = {c["name"] for c in inspector.get_columns("subscriptions")}
        if "user_id" not in existing_sub_cols:
            op.add_column("subscriptions", sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True))
            op.create_index("idx_subscriptions_user_status", "subscriptions", ["user_id", "status"])

    # 4. Create payment_transactions table if missing
    if "payment_transactions" not in existing_tables:
        op.create_table(
            "payment_transactions",
            sa.Column("id", UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("home_id", UUID(as_uuid=True), sa.ForeignKey("homes.id", ondelete="SET NULL"), nullable=True),
            sa.Column("subscription_id", UUID(as_uuid=True), sa.ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True),
            sa.Column("plan_id", UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("price_id", UUID(as_uuid=True), sa.ForeignKey("subscription_prices.id", ondelete="SET NULL"), nullable=True),
            sa.Column("coupon_id", UUID(as_uuid=True), sa.ForeignKey("coupons.id", ondelete="SET NULL"), nullable=True),
            sa.Column("amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
            sa.Column("discount_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
            sa.Column("tax_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
            sa.Column("final_amount", sa.Numeric(10, 2), server_default="0.00", nullable=False),
            sa.Column("currency", sa.String(3), server_default="USD", nullable=False),
            sa.Column("provider", sa.String(32), server_default="MOCK_GATEWAY", nullable=False),
            sa.Column("provider_transaction_id", sa.String(128), nullable=True),
            sa.Column("idempotency_key", sa.String(128), unique=True, nullable=True),
            sa.Column("status", sa.String(32), server_default="PENDING", nullable=False),
            sa.Column("failure_reason", sa.Text(), nullable=True),
            sa.Column("metadata_json", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("idx_pay_trans_user_status", "payment_transactions", ["user_id", "status"])
        op.create_index("idx_pay_trans_created", "payment_transactions", ["created_at"])
        op.create_index("idx_pay_trans_provider_id", "payment_transactions", ["provider_transaction_id"])
        op.create_index("idx_pay_trans_idempotency", "payment_transactions", ["idempotency_key"])


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    existing_tables = set(inspector.get_table_names())

    if "payment_transactions" in existing_tables:
        op.drop_table("payment_transactions")

    if "subscriptions" in existing_tables:
        existing_sub_cols = {c["name"] for c in inspector.get_columns("subscriptions")}
        if "user_id" in existing_sub_cols:
            op.drop_index("idx_subscriptions_user_status", table_name="subscriptions")
            op.drop_column("subscriptions", "user_id")

    if "subscription_plans" in existing_tables:
        existing_plan_cols = {c["name"] for c in inspector.get_columns("subscription_plans")}
        if "max_homes" in existing_plan_cols:
            op.drop_column("subscription_plans", "max_homes")

    if "users" in existing_tables:
        existing_user_cols = {c["name"] for c in inspector.get_columns("users")}
        if "free_home_consumed" in existing_user_cols:
            op.drop_index("ix_users_free_home_consumed", table_name="users")
            op.drop_column("users", "free_home_consumed")
