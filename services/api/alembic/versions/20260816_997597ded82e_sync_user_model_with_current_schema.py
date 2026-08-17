"""sync user model with current schema"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "997597ded82e"
down_revision: Union[str, None] = "20260813_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone_number", sa.String(32), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column("country_code", sa.String(8), nullable=True),
    )

    op.add_column(
        "users",
        sa.Column(
            "mobile_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "is_super_admin",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "system_role",
            sa.String(32),
            nullable=False,
            server_default="USER",
        ),
    )

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(255),
        nullable=True,
    )

    op.create_index(
        "ix_users_phone_number",
        "users",
        ["phone_number"],
        unique=True,
    )

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_phone_number", table_name="users")

    op.alter_column(
        "users",
        "email",
        existing_type=sa.String(255),
        nullable=False,
    )

    op.drop_column("users", "system_role")
    op.drop_column("users", "is_super_admin")
    op.drop_column("users", "mobile_verified")
    op.drop_column("users", "country_code")
    op.drop_column("users", "phone_number")
