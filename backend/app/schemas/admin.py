from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


# ── User list / detail (US-036) ───────────────────────────────────────────────


class UserSummary(BaseModel):
    id: int
    email: str | None
    username: str | None = None
    full_name: str
    role: str
    is_active: bool
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ── Admin-created OWNER account (demo/tester) ────────────────────────────────


class OwnerAccountCreate(BaseModel):
    full_name: str
    email: EmailStr

    @field_validator("full_name")
    @classmethod
    def full_name_not_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Le nom complet est requis")
        return v.strip()


class OwnerAccountCreated(BaseModel):
    id: int
    full_name: str
    email: str
    generated_password: str  # plaintext, returned exactly once — never persisted or re-exposed


# ── Plan assignment (US-040) ─────────────────────────────────────────────────


class AssignPlanRequest(BaseModel):
    plan_name: str  # starter | pro | business
    expires_at: datetime | None = None


# ── Fleet view (US-039) ──────────────────────────────────────────────────────


class AdminVehicleSummary(BaseModel):
    id: int
    name: str
    brand: str
    model: str
    license_plate: str
    status: str

    model_config = {"from_attributes": True}


class OwnerFleetResponse(BaseModel):
    owner_id: int
    owner_name: str
    owner_email: str
    vehicles: list[AdminVehicleSummary]


# ── Plan usage (US-046) ──────────────────────────────────────────────────────


class PlanDetails(BaseModel):
    name: str
    max_vehicles: int | None
    max_drivers: int | None
    has_export: bool
    price_fcfa: int

    model_config = {"from_attributes": True}


class PlanUsageResponse(BaseModel):
    plan: PlanDetails
    active_vehicles: int
    active_drivers: int
    expires_at: datetime | None
