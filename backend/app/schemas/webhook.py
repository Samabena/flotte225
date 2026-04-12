from datetime import datetime
from pydantic import BaseModel


class WebhookStatusResponse(BaseModel):
    configured: bool
    last_sent_at: datetime | None
    last_status_code: int | None

    class Config:
        from_attributes = True
