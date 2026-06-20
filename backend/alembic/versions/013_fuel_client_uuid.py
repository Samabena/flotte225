"""Add client_uuid to fuel_entries for idempotent offline sync.

Revision ID: 013
Revises: 012
Create Date: 2026-06-20
"""
import sqlalchemy as sa
from alembic import op

revision = "013"
down_revision = "012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "fuel_entries", sa.Column("client_uuid", sa.String(36), nullable=True)
    )
    op.create_unique_constraint(
        "uq_fuel_entries_client_uuid", "fuel_entries", ["client_uuid"]
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_fuel_entries_client_uuid", "fuel_entries", type_="unique"
    )
    op.drop_column("fuel_entries", "client_uuid")
