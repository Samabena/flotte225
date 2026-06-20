import datetime as dt
from typing import Literal

from pydantic import BaseModel, field_validator

ExpenseType = Literal[
    "Vidange",
    "Pneus",
    "Freins",
    "Révision",
    "Carrosserie",
    "Batterie",
    "Autre",
]


class MaintenanceExpenseCreate(BaseModel):
    date: dt.date
    odometer_km: int | None = None
    type: ExpenseType
    cost_fcfa: float
    location: str | None = None
    note: str | None = None

    @field_validator("cost_fcfa")
    @classmethod
    def cost_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Le coût doit être supérieur à 0")
        return v

    @field_validator("odometer_km")
    @classmethod
    def odometer_non_negative(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("Le kilométrage doit être >= 0")
        return v


class MaintenanceExpenseUpdate(BaseModel):
    date: dt.date | None = None
    odometer_km: int | None = None
    type: ExpenseType | None = None
    cost_fcfa: float | None = None
    location: str | None = None
    note: str | None = None

    @field_validator("cost_fcfa")
    @classmethod
    def cost_positive(cls, v: float | None) -> float | None:
        if v is not None and v <= 0:
            raise ValueError("Le coût doit être supérieur à 0")
        return v


class MaintenanceExpenseResponse(BaseModel):
    id: int
    vehicle_id: int
    date: dt.date
    odometer_km: int | None
    type: str
    cost_fcfa: float
    location: str | None
    note: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
