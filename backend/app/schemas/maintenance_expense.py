import datetime as dt

from pydantic import BaseModel, field_validator

# Common types are offered as suggestions in the UI ("Vidange", "Pneus", …),
# but the user may type any custom type ("Autre"). Stored verbatim; capped to
# the DB column width. "Vidange" keeps its special oil-change handling.
MAX_TYPE_LEN = 50


def _clean_type(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if not v:
        raise ValueError("Le type est obligatoire")
    if len(v) > MAX_TYPE_LEN:
        raise ValueError(f"Le type ne doit pas dépasser {MAX_TYPE_LEN} caractères")
    return v


class MaintenanceExpenseCreate(BaseModel):
    date: dt.date
    odometer_km: int | None = None
    type: str
    cost_fcfa: float
    location: str | None = None
    note: str | None = None
    client_uuid: str | None = None  # idempotency key for offline sync

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str) -> str:
        return _clean_type(v)

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
    type: str | None = None
    cost_fcfa: float | None = None
    location: str | None = None
    note: str | None = None

    @field_validator("type")
    @classmethod
    def type_valid(cls, v: str | None) -> str | None:
        return _clean_type(v)

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
    client_uuid: str | None
    created_at: dt.datetime

    model_config = {"from_attributes": True}
