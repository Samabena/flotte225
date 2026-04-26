from datetime import datetime
from pydantic import BaseModel


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
    ai_reports_per_month: int | None
    has_whatsapp: bool
    has_export: bool
    has_webhook: bool
    price_fcfa: int

    model_config = {"from_attributes": True}


class PlanUsageResponse(BaseModel):
    plan: PlanDetails
    active_vehicles: int
    active_drivers: int
    expires_at: datetime | None
