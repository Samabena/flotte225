from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MaintenanceExpense(Base):
    """A single maintenance/repair spending line for a vehicle.
    Distinct from the `maintenance` table (which holds compliance dates)."""

    __tablename__ = "maintenance_expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vehicle_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("vehicles.id"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    odometer_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Vidange | Pneus | Freins | Révision | Carrosserie | Batterie | Autre
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    cost_fcfa: Mapped[float] = mapped_column(Numeric(12, 2), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    note: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
