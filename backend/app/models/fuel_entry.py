from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, Date, Numeric, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FuelEntry(Base):
    __tablename__ = "fuel_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicles.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    odometer_km: Mapped[int] = mapped_column(Integer, nullable=False)
    quantity_litres: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    amount_fcfa: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    distance_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    consumption_per_100km: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
