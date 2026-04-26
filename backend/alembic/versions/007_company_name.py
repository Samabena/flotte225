"""add company_name to users

Revision ID: 007
Revises: 006
Create Date: 2026-04-22
"""
from alembic import op
import sqlalchemy as sa

revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("company_name", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "company_name")
