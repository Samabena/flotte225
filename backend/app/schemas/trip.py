from datetime import datetime

from pydantic import BaseModel


class TripResponse(BaseModel):
    id: int
    vehicle_id: int
    driver_id: int
    start_odometer: int
    end_odometer: int | None
    distance_km: int | None
    started_at: datetime
    ended_at: datetime | None

    model_config = {"from_attributes": True}
