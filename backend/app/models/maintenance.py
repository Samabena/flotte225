from datetime import datetime, date, timezone
from sqlalchemy import Integer, ForeignKey, Date, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Maintenance(Base):
    __tablename__ = "maintenance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicles.id"), unique=True, nullable=False)
    last_oil_change_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    insurance_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    inspection_expiry: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
