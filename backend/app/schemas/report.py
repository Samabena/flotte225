from datetime import date, datetime
from pydantic import BaseModel


class ReportGenerateResponse(BaseModel):
    status: str
    used: int
    limit: int | None


class ReportScheduleResponse(BaseModel):
    enabled: bool
    frequency: str | None
    last_sent_at: datetime | None
    last_status: str | None
    ai_reports_used_month: int
    usage_reset_at: date | None

    class Config:
        from_attributes = True


class ReportScheduleUpdate(BaseModel):
    enabled: bool
    frequency: str | None = None
