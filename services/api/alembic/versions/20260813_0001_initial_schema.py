"""initial schema

Revision ID: 20260813_0001
Revises: 
Create Date: 2026-08-13 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = '20260813_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. users
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(255), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 2. user_profiles
    op.create_table(
        'user_profiles',
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('display_name', sa.String(100), nullable=False),
        sa.Column('phone_number', sa.String(32), nullable=True),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('timezone', sa.String(64), nullable=False, default='UTC'),
        sa.Column('preferred_language', sa.String(10), nullable=False, default='en'),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 3. homes
    op.create_table(
        'homes',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('timezone', sa.String(64), nullable=False, default='UTC'),
        sa.Column('address', sa.Text(), nullable=True),
        sa.Column('avatar_url', sa.String(512), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )

    # 4. home_members
    op.create_table(
        'home_members',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('home_id', UUID(as_uuid=True), sa.ForeignKey('homes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role', sa.String(32), nullable=False),
        sa.Column('status', sa.String(32), nullable=False, default='ACTIVE'),
        sa.Column('joined_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('home_id', 'user_id', name='uq_home_members_home_user')
    )
    op.create_index('idx_home_members_lookup', 'home_members', ['home_id', 'user_id', 'status'])

    # 5. inventory_categories
    op.create_table(
        'inventory_categories',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('home_id', UUID(as_uuid=True), sa.ForeignKey('homes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(64), nullable=False),
        sa.Column('icon', sa.String(64), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False)
    )

    # 6. inventory_items
    op.create_table(
        'inventory_items',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('home_id', UUID(as_uuid=True), sa.ForeignKey('homes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('category_id', UUID(as_uuid=True), sa.ForeignKey('inventory_categories.id', ondelete='SET NULL'), nullable=True),
        sa.Column('name', sa.String(120), nullable=False),
        sa.Column('quantity', sa.Numeric(10, 2), nullable=False, default=1.0),
        sa.Column('unit', sa.String(32), nullable=False, default='pcs'),
        sa.Column('min_threshold', sa.Numeric(10, 2), nullable=True, default=1.0),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False, default='IN_STOCK'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('idx_inv_items_home_status', 'inventory_items', ['home_id', 'status'])

    # 7. tasks
    op.create_table(
        'tasks',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('home_id', UUID(as_uuid=True), sa.ForeignKey('homes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(160), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('priority', sa.String(16), nullable=False, default='MEDIUM'),
        sa.Column('status', sa.String(20), nullable=False, default='TODO'),
        sa.Column('assigned_to', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recurrence_rule', sa.String(64), nullable=True),
        sa.Column('created_by', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('idx_tasks_home_due', 'tasks', ['home_id', 'status', 'due_date'])

    # 8. bills
    op.create_table(
        'bills',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('home_id', UUID(as_uuid=True), sa.ForeignKey('homes.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(120), nullable=False),
        sa.Column('category', sa.String(64), nullable=False, default='Utilities'),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False, default='USD'),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('recurrence_interval', sa.String(32), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, default='UNPAID'),
        sa.Column('default_payer_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index('idx_bills_home_due', 'bills', ['home_id', 'status', 'due_date'])


def downgrade() -> None:
    op.drop_table('bills')
    op.drop_table('tasks')
    op.drop_table('inventory_items')
    op.drop_table('inventory_categories')
    op.drop_table('home_members')
    op.drop_table('homes')
    op.drop_table('user_profiles')
    op.drop_table('users')
