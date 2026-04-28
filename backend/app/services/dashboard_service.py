from decimal import Decimal

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.models.user import User
from app.schemas.dashboard import (
    ConsumptionIndicator,
    DashboardResponse,
    DriverStatus,
    FinancialSummary,
    MonthlySpend,
    VehicleSpend,
)
from app.services.alert_service import compute_alerts


def get_dashboard_data(db: Session, owner_id: int) -> DashboardResponse:
    return DashboardResponse(
        financial=_get_financial_summary(db, owner_id),
        consumption=_get_consumption_indicators(db, owner_id),
        drivers=_get_driver_statuses(db, owner_id),
        alerts=compute_alerts(db, owner_id),
    )


# ── Financial ─────────────────────────────────────────────────────────────────


def _get_financial_summary(db: Session, owner_id: int) -> FinancialSummary:
    total = (
        db.query(func.coalesce(func.sum(FuelEntry.amount_fcfa), 0))
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .scalar()
    )

    spend_rows = (
        db.query(
            Vehicle.id, Vehicle.name, func.sum(FuelEntry.amount_fcfa).label("spend")
        )
        .join(FuelEntry, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .group_by(Vehicle.id, Vehicle.name)
        .order_by(func.sum(FuelEntry.amount_fcfa).desc())
        .all()
    )
    spend_per_vehicle = [
        VehicleSpend(
            vehicle_id=r.id, vehicle_name=r.name, spend_fcfa=Decimal(str(r.spend or 0))
        )
        for r in spend_rows
    ]

    year_col = extract("year", FuelEntry.date)
    month_col = extract("month", FuelEntry.date)
    monthly_rows = (
        db.query(
            year_col.label("yr"),
            month_col.label("mo"),
            func.sum(FuelEntry.amount_fcfa).label("spend"),
        )
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .group_by(year_col, month_col)
        .order_by(year_col, month_col)
        .all()
    )
    # Keep last 12 months max
    monthly_trend = [
        MonthlySpend(
            month=f"{int(r.yr):04d}-{int(r.mo):02d}",
            spend_fcfa=Decimal(str(r.spend or 0)),
        )
        for r in monthly_rows
    ][-12:]

    return FinancialSummary(
        total_spend_fcfa=Decimal(str(total)),
        spend_per_vehicle=spend_per_vehicle,
        monthly_trend=monthly_trend,
    )


# ── Consumption ───────────────────────────────────────────────────────────────


def _get_consumption_indicators(
    db: Session, owner_id: int
) -> list[ConsumptionIndicator]:
    rows = (
        db.query(
            Vehicle.id,
            Vehicle.name,
            Vehicle.brand,
            Vehicle.model,
            func.avg(FuelEntry.consumption_per_100km).label("avg_consumption"),
            func.count(FuelEntry.id).label("entry_count"),
        )
        .outerjoin(FuelEntry, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id, Vehicle.status != "archived")
        .group_by(Vehicle.id, Vehicle.name, Vehicle.brand, Vehicle.model)
        .all()
    )
    result = []
    for r in rows:
        avg = (
            Decimal(str(r.avg_consumption)).quantize(Decimal("0.01"))
            if r.avg_consumption is not None
            else None
        )
        result.append(
            ConsumptionIndicator(
                vehicle_id=r.id,
                vehicle_name=r.name,
                brand=r.brand,
                model=r.model,
                avg_consumption_per_100km=avg,
                entry_count=r.entry_count or 0,
            )
        )
    return result


# ── Drivers ───────────────────────────────────────────────────────────────────


def _get_driver_statuses(db: Session, owner_id: int) -> list[DriverStatus]:
    # New system: drivers provisioned directly by this owner
    direct_ids = {
        r.id
        for r in db.query(User.id)
        .filter(User.owner_id == owner_id, User.role == "DRIVER")
        .all()
    }
    # Legacy: drivers linked via vehicle assignment
    legacy_ids = {
        r.driver_id
        for r in db.query(VehicleDriver.driver_id)
        .join(Vehicle, VehicleDriver.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .distinct()
        .all()
    }
    all_ids = direct_ids | legacy_ids
    if not all_ids:
        return []

    drivers = db.query(User).filter(User.id.in_(all_ids)).all()

    active_vehicle_ids = [d.active_vehicle_id for d in drivers if d.active_vehicle_id]
    vehicles_map: dict[int, str] = {}
    if active_vehicle_ids:
        for v in db.query(Vehicle).filter(Vehicle.id.in_(active_vehicle_ids)).all():
            vehicles_map[v.id] = v.name

    return [
        DriverStatus(
            driver_id=d.id,
            full_name=d.full_name,
            driving_status=d.driving_status,
            active_vehicle_id=d.active_vehicle_id,
            active_vehicle_name=(
                vehicles_map.get(d.active_vehicle_id) if d.active_vehicle_id else None
            ),
        )
        for d in drivers
    ]
