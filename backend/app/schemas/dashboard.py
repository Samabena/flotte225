from decimal import Decimal
from pydantic import BaseModel

from app.schemas.alert import AlertResponse


class VehicleSpend(BaseModel):
    vehicle_id: int
    vehicle_name: str
    fuel_fcfa: Decimal
    maintenance_fcfa: Decimal
    spend_fcfa: Decimal  # fuel + maintenance


class DriverSpend(BaseModel):
    driver_id: int | None  # None = unassigned vehicles ("Non attribué")
    driver_name: str
    fuel_fcfa: Decimal  # fuel logged by this driver
    maintenance_fcfa: Decimal  # maintenance of vehicles assigned to this driver
    spend_fcfa: Decimal  # fuel + maintenance


class MonthlySpend(BaseModel):
    month: str  # e.g. "2026-03"
    spend_fcfa: Decimal


class FinancialSummary(BaseModel):
    total_spend_fcfa: Decimal  # grand total = fuel + maintenance
    fuel_total_fcfa: Decimal
    maintenance_total_fcfa: Decimal
    total_distance_km: int
    cost_per_km_fcfa: Decimal
    spend_per_vehicle: list[VehicleSpend]  # fuel + maintenance, per vehicle
    spend_per_driver: list[DriverSpend]  # fuel (logged) + maintenance (assigned)
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
