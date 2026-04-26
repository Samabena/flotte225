from datetime import date, datetime, timedelta
from pydantic import BaseModel, model_validator


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


class TemplateReportRequest(BaseModel):
    """Date range for a deterministic template report. Defaults to last 30 days."""

    date_from: date | None = None
    date_to: date | None = None

    @model_validator(mode="after")
    def _fill_defaults_and_validate(self):
        today = date.today()
        if self.date_to is None:
            self.date_to = today
        if self.date_from is None:
            self.date_from = self.date_to - timedelta(days=30)
        if self.date_from > self.date_to:
            raise ValueError("date_from doit être antérieure ou égale à date_to")
        return self
