from datetime import datetime, timezone
from sqlalchemy import String, Boolean, Integer, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # OWNER / SUPER_ADMIN login identifier — NULL for DRIVER rows
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    # DRIVER login identifier — NULL for OWNER / SUPER_ADMIN rows
    username: Mapped[str | None] = mapped_column(
        String(100), unique=True, nullable=True
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # OWNER | DRIVER | SUPER_ADMIN
    full_name: Mapped[str] = mapped_column(String(100), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20))
    whatsapp_number: Mapped[str | None] = mapped_column(String(20))
    email_alerts_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # DRIVER only — owner disables login without deleting the account
    is_disabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Driver-specific state
    driving_status: Mapped[bool] = mapped_column(Boolean, default=False)
    active_vehicle_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("vehicles.id", use_alter=True, name="fk_users_active_vehicle_id"),
        nullable=True,
    )

    # DRIVER only — FK to the OWNER who provisioned this driver account
    owner_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("users.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
