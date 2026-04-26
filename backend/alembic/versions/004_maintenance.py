"""maintenance records table

Revision ID: 004
Revises: 003
Create Date: 2026-04-08
"""
from alembic import op
import sqlalchemy as sa

revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "maintenance",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), unique=True, nullable=False),
        sa.Column("last_oil_change_km", sa.Integer(), nullable=True),
        sa.Column("insurance_expiry", sa.Date(), nullable=True),
        sa.Column("inspection_expiry", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("maintenance")
