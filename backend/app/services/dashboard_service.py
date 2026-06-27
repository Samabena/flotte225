from decimal import Decimal

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.models.maintenance_expense import MaintenanceExpense
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.models.user import User
from app.schemas.dashboard import (
    ConsumptionIndicator,
    DashboardResponse,
    DriverSpend,
    DriverStatus,
    FinancialSummary,
    MonthlySpend,
    VehicleSpend,
)
from app.services.alert_service import compute_alerts


def _vehicle_driver_map(db: Session, owner_id: int) -> dict[int, tuple[int, str]]:
    """Map each of the owner's vehicles to its most-recently-assigned driver.

    Maintenance is attributed "par chauffeur" through this link. A vehicle with
    several assignments resolves to the latest one; unassigned vehicles are
    absent (callers bucket them as "Non attribué")."""
    rows = (
        db.query(
            VehicleDriver.vehicle_id,
            VehicleDriver.driver_id,
            User.full_name,
        )
        .join(Vehicle, VehicleDriver.vehicle_id == Vehicle.id)
        .join(User, VehicleDriver.driver_id == User.id)
        .filter(Vehicle.owner_id == owner_id)
        .order_by(VehicleDriver.vehicle_id, VehicleDriver.assigned_at.desc())
        .all()
    )
    result: dict[int, tuple[int, str]] = {}
    for r in rows:
        if r.vehicle_id not in result:  # first seen = most recent assignment
            result[r.vehicle_id] = (r.driver_id, r.full_name)
    return result


def get_dashboard_data(db: Session, owner_id: int) -> DashboardResponse:
    return DashboardResponse(
        financial=_get_financial_summary(db, owner_id),
        consumption=_get_consumption_indicators(db, owner_id),
        drivers=_get_driver_statuses(db, owner_id),
        alerts=compute_alerts(db, owner_id),
    )


# ── Financial ─────────────────────────────────────────────────────────────────


def _get_financial_summary(db: Session, owner_id: int) -> FinancialSummary:
    fuel_total = (
        db.query(func.coalesce(func.sum(FuelEntry.amount_fcfa), 0))
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .scalar()
    )

    maintenance_total = (
        db.query(func.coalesce(func.sum(MaintenanceExpense.cost_fcfa), 0))
        .join(Vehicle, MaintenanceExpense.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .scalar()
    )

    grand_total = Decimal(str(fuel_total)) + Decimal(str(maintenance_total))

    total_distance = (
        db.query(func.coalesce(func.sum(FuelEntry.distance_km), 0))
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .scalar()
    ) or 0
    total_distance = int(total_distance)
    cost_per_km = (
        (grand_total / Decimal(total_distance)).quantize(Decimal("0.01"))
        if total_distance > 0
        else Decimal("0")
    )

    # Per-vehicle spend = fuel + maintenance (merged from two grouped queries).
    name_map = {
        v.id: v.name
        for v in db.query(Vehicle.id, Vehicle.name)
        .filter(Vehicle.owner_id == owner_id)
        .all()
    }
    fuel_by_vehicle = {
        r.vehicle_id: Decimal(str(r.spend or 0))
        for r in db.query(
            FuelEntry.vehicle_id, func.sum(FuelEntry.amount_fcfa).label("spend")
        )
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .group_by(FuelEntry.vehicle_id)
        .all()
    }
    maint_by_vehicle = {
        r.vehicle_id: Decimal(str(r.spend or 0))
        for r in db.query(
            MaintenanceExpense.vehicle_id,
            func.sum(MaintenanceExpense.cost_fcfa).label("spend"),
        )
        .join(Vehicle, MaintenanceExpense.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .group_by(MaintenanceExpense.vehicle_id)
        .all()
    }
    spend_per_vehicle = []
    for vid, name in name_map.items():
        fuel = fuel_by_vehicle.get(vid, Decimal("0"))
        maint = maint_by_vehicle.get(vid, Decimal("0"))
        if fuel == 0 and maint == 0:
            continue
        spend_per_vehicle.append(
            VehicleSpend(
                vehicle_id=vid,
                vehicle_name=name,
                fuel_fcfa=fuel,
                maintenance_fcfa=maint,
                spend_fcfa=fuel + maint,
            )
        )
    spend_per_vehicle.sort(key=lambda r: r.spend_fcfa, reverse=True)

    # Spend "par chauffeur" = fuel (attributed to whoever logged the fill-up)
    # + maintenance (attributed via the vehicle's assigned driver).
    driver_map = _vehicle_driver_map(db, owner_id)
    driver_names: dict[int | None, str] = {None: "Non attribué"}

    fuel_by_driver: dict[int | None, Decimal] = {}
    for r in (
        db.query(
            FuelEntry.driver_id, func.sum(FuelEntry.amount_fcfa).label("spend")
        )
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .group_by(FuelEntry.driver_id)
        .all()
    ):
        fuel_by_driver[r.driver_id] = Decimal(str(r.spend or 0))

    maint_by_driver: dict[int | None, Decimal] = {}
    for vid, maint in maint_by_vehicle.items():
        if maint == 0:
            continue
        driver_id, driver_name = driver_map.get(vid, (None, "Non attribué"))
        maint_by_driver[driver_id] = maint_by_driver.get(driver_id, Decimal("0")) + maint
        driver_names[driver_id] = driver_name

    # Resolve names for drivers that appear only via fuel.
    missing_ids = [
        did
        for did in fuel_by_driver
        if did is not None and did not in driver_names
    ]
    if missing_ids:
        for u in db.query(User.id, User.full_name).filter(User.id.in_(missing_ids)).all():
            driver_names[u.id] = u.full_name

    spend_per_driver = []
    for did in set(fuel_by_driver) | set(maint_by_driver):
        fuel = fuel_by_driver.get(did, Decimal("0"))
        maint = maint_by_driver.get(did, Decimal("0"))
        spend_per_driver.append(
            DriverSpend(
                driver_id=did,
                driver_name=driver_names.get(did, "Non attribué"),
                fuel_fcfa=fuel,
                maintenance_fcfa=maint,
                spend_fcfa=fuel + maint,
            )
        )
    spend_per_driver.sort(key=lambda r: r.spend_fcfa, reverse=True)

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
        total_spend_fcfa=grand_total,
        fuel_total_fcfa=Decimal(str(fuel_total)),
        maintenance_total_fcfa=Decimal(str(maintenance_total)),
        total_distance_km=total_distance,
        cost_per_km_fcfa=cost_per_km,
        spend_per_vehicle=spend_per_vehicle,
        spend_per_driver=spend_per_driver,
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
