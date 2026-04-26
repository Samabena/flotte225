import datetime as dt
from pydantic import BaseModel


class MaintenanceUpdate(BaseModel):
    last_oil_change_km: int | None = None
    insurance_expiry: dt.date | None = None
    inspection_expiry: dt.date | None = None


class MaintenanceResponse(BaseModel):
    id: int
    vehicle_id: int
    last_oil_change_km: int | None
    insurance_expiry: dt.date | None
    inspection_expiry: dt.date | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}
