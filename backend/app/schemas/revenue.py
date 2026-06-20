import datetime as dt

from pydantic import BaseModel, field_validator


class RevenueCreate(BaseModel):
    date: dt.date
    amount_fcfa: float
    note: str | None = None
    client_uuid: str | None = None  # idempotency key for offline sync

    @field_validator("amount_fcfa")
    @classmethod
    def amount_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Le montant doit être supérieur à 0")
        return v


class RevenueResponse(BaseModel):
    id: int
    vehicle_id: int
    driver_id: int | None
    date: dt.date
    amount_fcfa: float
    note: str | None
    client_uuid: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
