"""Add maintenance_expenses table — per-vehicle repair/maintenance spending log.

Revision ID: 012
Revises: 011
Create Date: 2026-06-20
"""
import sqlalchemy as sa
from alembic import op

revision = "012"
down_revision = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance_expenses",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("odometer_km", sa.Integer(), nullable=True),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("cost_fcfa", sa.Numeric(12, 2), nullable=False),
        sa.Column("location", sa.String(255), nullable=True),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_maintenance_expenses_vehicle_id", "maintenance_expenses", ["vehicle_id"]
    )


def downgrade() -> None:
    op.drop_index(
        "ix_maintenance_expenses_vehicle_id", table_name="maintenance_expenses"
    )
    op.drop_table("maintenance_expenses")
