from decimal import Decimal
from pydantic import BaseModel

from app.schemas.alert import AlertResponse


class VehicleSpend(BaseModel):
    vehicle_id: int
    vehicle_name: str
    spend_fcfa: Decimal


class MonthlySpend(BaseModel):
    month: str  # e.g. "2026-03"
    spend_fcfa: Decimal


class FinancialSummary(BaseModel):
    total_spend_fcfa: Decimal
    spend_per_vehicle: list[VehicleSpend]
    monthly_trend: list[MonthlySpend]


class ConsumptionIndicator(BaseModel):
    vehicle_id: int
    vehicle_name: str
    brand: str
    model: str
    avg_consumption_per_100km: Decimal | None
    entry_count: int


class DriverStatus(BaseModel):
    driver_id: int
    full_name: str
    driving_status: bool
    active_vehicle_id: int | None
    active_vehicle_name: str | None


class DashboardResponse(BaseModel):
    financial: FinancialSummary
    consumption: list[ConsumptionIndicator]
    drivers: list[DriverStatus]
    alerts: list[AlertResponse]
