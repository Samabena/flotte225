"""Add trip_logs table — driver start/end odometer per driving session.

Revision ID: 011
Revises: 010
Create Date: 2026-06-20
"""
import sqlalchemy as sa
from alembic import op

revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trip_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("start_odometer", sa.Integer(), nullable=False),
        sa.Column("end_odometer", sa.Integer(), nullable=True),
        sa.Column("distance_km", sa.Integer(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("client_uuid", name="uq_trip_logs_client_uuid"),
    )
    op.create_index("ix_trip_logs_vehicle_id", "trip_logs", ["vehicle_id"])
    op.create_index("ix_trip_logs_driver_id", "trip_logs", ["driver_id"])


def downgrade() -> None:
    op.drop_index("ix_trip_logs_driver_id", table_name="trip_logs")
    op.drop_index("ix_trip_logs_vehicle_id", table_name="trip_logs")
    op.drop_table("trip_logs")
