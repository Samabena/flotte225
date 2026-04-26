import datetime as dt
from decimal import Decimal
from pydantic import BaseModel, field_validator


class FuelEntryCreate(BaseModel):
    vehicle_id: int
    date: dt.date
    odometer_km: int
    quantity_litres: Decimal
    amount_fcfa: Decimal

    @field_validator("odometer_km")
    @classmethod
    def odometer_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Le kilométrage doit être supérieur à 0")
        return v

    @field_validator("quantity_litres", "amount_fcfa")
    @classmethod
    def positive_decimal(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("La valeur doit être supérieure à 0")
        return v


class FuelEntryUpdate(BaseModel):
    date: dt.date | None = None
    odometer_km: int | None = None
    quantity_litres: Decimal | None = None
    amount_fcfa: Decimal | None = None

    @field_validator("odometer_km")
    @classmethod
    def odometer_positive(cls, v: int | None) -> int | None:
        if v is not None and v <= 0:
            raise ValueError("Le kilométrage doit être supérieur à 0")
        return v

    @field_validator("quantity_litres", "amount_fcfa")
    @classmethod
    def positive_decimal(cls, v: Decimal | None) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("La valeur doit être supérieure à 0")
        return v


class FuelEntryResponse(BaseModel):
    id: int
    vehicle_id: int
    driver_id: int
    date: dt.date
    odometer_km: int
    quantity_litres: Decimal
    amount_fcfa: Decimal
    distance_km: int | None
    consumption_per_100km: Decimal | None
    created_at: dt.datetime
    updated_at: dt.datetime

    model_config = {"from_attributes": True}
