"""Add route/GPS columns to fuel_entries for map tracking feature.

Revision ID: 010
Revises: 009
Create Date: 2026-05-10
"""
import sqlalchemy as sa
from alembic import op

revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("fuel_entries", sa.Column("departure_place", sa.String(255), nullable=True))
    op.add_column("fuel_entries", sa.Column("departure_lat", sa.Numeric(10, 7), nullable=True))
    op.add_column("fuel_entries", sa.Column("departure_lng", sa.Numeric(10, 7), nullable=True))
    op.add_column("fuel_entries", sa.Column("destination_place", sa.String(255), nullable=True))
    op.add_column("fuel_entries", sa.Column("destination_lat", sa.Numeric(10, 7), nullable=True))
    op.add_column("fuel_entries", sa.Column("destination_lng", sa.Numeric(10, 7), nullable=True))
    op.add_column("fuel_entries", sa.Column("route_distance_km", sa.Numeric(8, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("fuel_entries", "route_distance_km")
    op.drop_column("fuel_entries", "destination_lng")
    op.drop_column("fuel_entries", "destination_lat")
    op.drop_column("fuel_entries", "destination_place")
    op.drop_column("fuel_entries", "departure_lng")
    op.drop_column("fuel_entries", "departure_lat")
    op.drop_column("fuel_entries", "departure_place")
