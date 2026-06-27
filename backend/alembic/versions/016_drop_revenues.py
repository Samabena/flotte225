"""Drop revenues table — recette feature removed.

Revision ID: 016
Revises: 015
Create Date: 2026-06-27
"""
import sqlalchemy as sa
from alembic import op

revision = "016"
down_revision = "015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_revenues_vehicle_id", table_name="revenues")
    op.drop_table("revenues")


def downgrade() -> None:
    op.create_table(
        "revenues",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("amount_fcfa", sa.Numeric(12, 2), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column("client_uuid", sa.String(36), nullable=True),
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
        sa.UniqueConstraint("client_uuid", name="uq_revenues_client_uuid"),
    )
    op.create_index("ix_revenues_vehicle_id", "revenues", ["vehicle_id"])
