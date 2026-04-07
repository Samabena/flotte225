from datetime import datetime, timezone
from sqlalchemy import Integer, ForeignKey, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB
from app.core.database import Base


class ActivityLog(Base):
    __tablename__ = "activity_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    vehicle_id: Mapped[int] = mapped_column(Integer, ForeignKey("vehicles.id"), nullable=False)
    fuel_entry_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("fuel_entries.id", ondelete="SET NULL"), nullable=True)
    action: Mapped[str] = mapped_column(String(20), nullable=False)  # CREATE | UPDATE | DELETE
    data_before: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    data_after: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
