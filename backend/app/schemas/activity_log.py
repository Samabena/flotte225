from datetime import datetime
from pydantic import BaseModel


class ActivityLogResponse(BaseModel):
    id: int
    owner_id: int
    driver_id: int
    vehicle_id: int
    fuel_entry_id: int | None
    action: str
    data_before: dict | None
    data_after: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
