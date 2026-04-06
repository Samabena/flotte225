from datetime import datetime, timezone
from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)  # starter | pro | business
    max_vehicles: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    max_drivers: Mapped[int | None] = mapped_column(Integer, nullable=True)
    price_fcfa: Mapped[int] = mapped_column(Integer, nullable=False)
    ai_reports_per_month: Mapped[int | None] = mapped_column(Integer, nullable=True)  # NULL = unlimited
    has_whatsapp: Mapped[bool] = mapped_column(Boolean, default=False)
    has_export: Mapped[bool] = mapped_column(Boolean, default=False)
    has_webhook: Mapped[bool] = mapped_column(Boolean, default=False)


class OwnerSubscription(Base):
    __tablename__ = "owner_subscriptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    plan_id: Mapped[int] = mapped_column(Integer, ForeignKey("subscription_plans.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    assigned_by: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
