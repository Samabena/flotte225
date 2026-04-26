from datetime import date, datetime, timezone
from sqlalchemy import Integer, ForeignKey, DateTime, Boolean, String, Date
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class ReportSchedule(Base):
    __tablename__ = "report_schedules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id"), unique=True, nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    frequency: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # weekly | monthly
    last_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_status: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # sent | failed
    ai_reports_used_month: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0
    )
    usage_reset_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
