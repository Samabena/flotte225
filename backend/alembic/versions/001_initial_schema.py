"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-04-06
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 1. subscription_plans (no FK deps) ──────────────────────────────────
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(20), unique=True, nullable=False),
        sa.Column("max_vehicles", sa.Integer(), nullable=True),
        sa.Column("max_drivers", sa.Integer(), nullable=True),
        sa.Column("price_fcfa", sa.Integer(), nullable=False),
        sa.Column("ai_reports_per_month", sa.Integer(), nullable=True),
        sa.Column("has_whatsapp", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_export", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("has_webhook", sa.Boolean(), nullable=False, server_default="false"),
    )

    # ── 2. vehicles (owner_id FK added later — circular dep with users) ─────
    op.create_table(
        "vehicles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("plate_number", sa.String(20), unique=True, nullable=False),
        sa.Column("brand", sa.String(50), nullable=False),
        sa.Column("model", sa.String(50), nullable=False),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("fuel_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── 3. users (active_vehicle_id FK added later — circular dep) ──────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=False),
        sa.Column("phone", sa.String(20), nullable=True),
        sa.Column("whatsapp_number", sa.String(20), nullable=True),
        sa.Column("is_verified", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("driving_status", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("active_vehicle_id", sa.Integer(), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── 4. Cross-table FKs (circular dep resolution) ────────────────────────
    op.create_foreign_key(
        "fk_vehicles_owner_id", "vehicles", "users", ["owner_id"], ["id"]
    )
    op.create_foreign_key(
        "fk_users_active_vehicle_id", "users", "vehicles", ["active_vehicle_id"], ["id"]
    )

    # ── 5. otp_codes ─────────────────────────────────────────────────────────
    op.create_table(
        "otp_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("code", sa.String(6), nullable=False),
        sa.Column("purpose", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # ── 6. owner_subscriptions ───────────────────────────────────────────────
    op.create_table(
        "owner_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id",
            sa.Integer(),
            sa.ForeignKey("users.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("subscription_plans.id"),
            nullable=False,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("owner_subscriptions")
    op.drop_table("otp_codes")
    op.drop_constraint("fk_users_active_vehicle_id", "users", type_="foreignkey")
    op.drop_constraint("fk_vehicles_owner_id", "vehicles", type_="foreignkey")
    op.drop_table("users")
    op.drop_table("vehicles")
    op.drop_table("subscription_plans")
