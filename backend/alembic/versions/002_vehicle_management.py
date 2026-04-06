"""vehicle management: update vehicles table + add vehicle_drivers

Revision ID: 002
Revises: 001
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Update vehicles table ────────────────────────────────────────────────
    # Rename plate_number → license_plate
    op.alter_column("vehicles", "plate_number", new_column_name="license_plate")

    # Add new required columns
    op.add_column("vehicles", sa.Column("name", sa.String(255), nullable=True))
    op.add_column("vehicles", sa.Column("vin", sa.String(50), nullable=True))
    op.add_column("vehicles", sa.Column("initial_mileage", sa.Integer(), nullable=True, server_default="0"))

    # Backfill name with brand+model for any existing rows, then make NOT NULL
    op.execute("UPDATE vehicles SET name = brand || ' ' || model WHERE name IS NULL")
    op.alter_column("vehicles", "name", nullable=False)
    op.alter_column("vehicles", "initial_mileage", nullable=False)

    # ── vehicle_drivers junction table ───────────────────────────────────────
    op.create_table(
        "vehicle_drivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("vehicle_id", "driver_id", name="uq_vehicle_driver"),
    )


def downgrade() -> None:
    op.drop_table("vehicle_drivers")
    op.drop_column("vehicles", "initial_mileage")
    op.drop_column("vehicles", "vin")
    op.drop_column("vehicles", "name")
    op.alter_column("vehicles", "license_plate", new_column_name="plate_number")
