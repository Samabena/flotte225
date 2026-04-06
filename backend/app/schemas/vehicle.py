from datetime import datetime
from typing import Literal
from pydantic import BaseModel, field_validator


class VehicleCreate(BaseModel):
    name: str
    brand: str
    model: str
    year: int | None = None
    license_plate: str
    vin: str | None = None
    fuel_type: Literal["Essence", "Diesel", "GPL"]
    initial_mileage: int
    driver_ids: list[int] | None = None  # optional initial assignments

    @field_validator("name", "brand", "model", "license_plate")
    @classmethod
    def not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Ce champ est requis")
        return v.strip()

    @field_validator("initial_mileage")
    @classmethod
    def mileage_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Le kilométrage initial doit être >= 0")
        return v


class VehicleUpdate(BaseModel):
    name: str | None = None
    brand: str | None = None
    model: str | None = None
    year: int | None = None
    license_plate: str | None = None
    vin: str | None = None
    fuel_type: Literal["Essence", "Diesel", "GPL"] | None = None


class DriverSummary(BaseModel):
    id: int
    full_name: str
    email: str
    driving_status: bool

    model_config = {"from_attributes": True}


class VehicleResponse(BaseModel):
    id: int
    name: str
    brand: str
    model: str
    year: int | None
    license_plate: str
    vin: str | None
    fuel_type: str
    initial_mileage: int
    status: str
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class AssignDriverRequest(BaseModel):
    driver_id: int


class ActivateRequest(BaseModel):
    vehicle_id: int
