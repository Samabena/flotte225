"""driver access control — username, is_disabled, make email nullable

Revision ID: 006
Revises: 005
Create Date: 2026-04-19
"""
from alembic import op
import sqlalchemy as sa

revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Allow email to be NULL for driver rows (they use username instead)
    op.alter_column("users", "email", nullable=True)

    # Remove the UNIQUE constraint on email before making it nullable-safe
    # (PostgreSQL allows multiple NULLs in a UNIQUE column, so this is fine)

    # Add username — unique login identifier for DRIVER-role users
    op.add_column(
        "users",
        sa.Column("username", sa.String(100), unique=True, nullable=True),
    )

    # Add is_disabled — owner-controlled flag to block driver login
    op.add_column(
        "users",
        sa.Column(
            "is_disabled",
            sa.Boolean(),
            nullable=False,
            server_default="false",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_disabled")
    op.drop_column("users", "username")
    op.alter_column("users", "email", nullable=False)
