"""Remove AI report, WhatsApp and webhook features.

Drops the feature-only tables (report_schedules, webhook_states) and the
now-unused columns on subscription_plans and users.

Revision ID: 017
Revises: 016
Create Date: 2026-06-27
"""
import sqlalchemy as sa
from alembic import op

revision = "017"
down_revision = "016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF EXISTS guards: environments have drifted (e.g. webhook_states was
    # already absent in some DBs), so make the teardown idempotent.
    op.execute("DROP TABLE IF EXISTS report_schedules")
    op.execute("DROP TABLE IF EXISTS webhook_states")
    op.execute(
        "ALTER TABLE subscription_plans DROP COLUMN IF EXISTS ai_reports_per_month"
    )
    op.execute("ALTER TABLE subscription_plans DROP COLUMN IF EXISTS has_whatsapp")
    op.execute("ALTER TABLE subscription_plans DROP COLUMN IF EXISTS has_webhook")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS whatsapp_number")


def downgrade() -> None:
    op.add_column(
        "users", sa.Column("whatsapp_number", sa.String(20), nullable=True)
    )
    op.add_column(
        "subscription_plans",
        sa.Column("has_webhook", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("has_whatsapp", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "subscription_plans",
        sa.Column("ai_reports_per_month", sa.Integer(), nullable=True),
    )
    op.create_table(
        "webhook_states",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_code", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "report_schedules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "owner_id", sa.Integer(), sa.ForeignKey("users.id"), unique=True, nullable=False
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("frequency", sa.String(20), nullable=True),
        sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status", sa.String(20), nullable=True),
        sa.Column(
            "ai_reports_used_month", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("usage_reset_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
