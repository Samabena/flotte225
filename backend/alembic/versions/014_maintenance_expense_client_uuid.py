"""Add client_uuid to maintenance_expenses for idempotent offline sync.

Revision ID: 014
Revises: 013
Create Date: 2026-06-20
"""
import sqlalchemy as sa
from alembic import op

revision = "014"
down_revision = "013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "maintenance_expenses", sa.Column("client_uuid", sa.String(36), nullable=True)
    )
    op.create_unique_constraint(
        "uq_maintenance_expenses_client_uuid",
        "maintenance_expenses",
        ["client_uuid"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_maintenance_expenses_client_uuid",
        "maintenance_expenses",
        type_="unique",
    )
    op.drop_column("maintenance_expenses", "client_uuid")
