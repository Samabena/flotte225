from datetime import datetime, timezone, timedelta
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.models.activity_log import ActivityLog
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.models.user import User
from app.schemas.fuel_entry import FuelEntryCreate, FuelEntryUpdate


# ── helpers ───────────────────────────────────────────────────────────────────

def _entry_snapshot(entry: FuelEntry) -> dict:
    return {
        "id": entry.id,
        "vehicle_id": entry.vehicle_id,
        "driver_id": entry.driver_id,
        "date": str(entry.date),
        "odometer_km": entry.odometer_km,
        "quantity_litres": str(entry.quantity_litres),
        "amount_fcfa": str(entry.amount_fcfa),
        "distance_km": entry.distance_km,
        "consumption_per_100km": str(entry.consumption_per_100km) if entry.consumption_per_100km else None,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def _get_previous_odometer(db: Session, vehicle_id: int, exclude_entry_id: int | None = None) -> int:
    """Return the highest odometer reading for this vehicle (excluding a given entry)."""
    q = db.query(FuelEntry).filter(FuelEntry.vehicle_id == vehicle_id)
    if exclude_entry_id is not None:
        q = q.filter(FuelEntry.id != exclude_entry_id)
    last = q.order_by(FuelEntry.odometer_km.desc()).first()
    if last:
        return last.odometer_km
    vehicle = db.get(Vehicle, vehicle_id)
    return vehicle.initial_mileage if vehicle else 0


def _compute_derived(quantity_litres: float, odometer_km: int, previous_odometer: int) -> tuple[int | None, float | None]:
    distance_km = odometer_km - previous_odometer
    if distance_km <= 0:
        return None, None
    consumption = round(float(quantity_litres) / distance_km * 100, 2)
    return distance_km, consumption


def _create_log(
    db: Session,
    owner_id: int,
    driver_id: int,
    vehicle_id: int,
    fuel_entry_id: int | None,
    action: str,
    data_before: dict | None,
    data_after: dict | None,
) -> None:
    log = ActivityLog(
        owner_id=owner_id,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        fuel_entry_id=fuel_entry_id,
        action=action,
        data_before=data_before,
        data_after=data_after,
    )
    db.add(log)


def _get_owner_id_for_vehicle(db: Session, vehicle_id: int) -> int:
    vehicle = db.get(Vehicle, vehicle_id)
    return vehicle.owner_id


# ── US-010: Submit a fuel entry ───────────────────────────────────────────────

def create_fuel_entry(db: Session, driver: User, data: FuelEntryCreate) -> FuelEntry:
    # Driver must be active
    if not driver.driving_status:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Activez votre statut de conduite avant de soumettre une entrée carburant",
        )

    # Driver must be active on this specific vehicle
    if driver.active_vehicle_id != data.vehicle_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas en train de conduire ce véhicule",
        )

    # Driver must be assigned to this vehicle
    assignment = db.query(VehicleDriver).filter(
        VehicleDriver.driver_id == driver.id,
        VehicleDriver.vehicle_id == data.vehicle_id,
    ).first()
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce véhicule",
        )

    # Odometer must be strictly greater than the previous reading
    previous_odometer = _get_previous_odometer(db, data.vehicle_id)
    if data.odometer_km <= previous_odometer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le kilométrage ({data.odometer_km} km) doit être supérieur au dernier relevé ({previous_odometer} km)",
        )

    distance_km, consumption = _compute_derived(float(data.quantity_litres), data.odometer_km, previous_odometer)

    entry = FuelEntry(
        vehicle_id=data.vehicle_id,
        driver_id=driver.id,
        date=data.date,
        odometer_km=data.odometer_km,
        quantity_litres=data.quantity_litres,
        amount_fcfa=data.amount_fcfa,
        distance_km=distance_km,
        consumption_per_100km=consumption,
    )
    db.add(entry)
    db.flush()  # get entry.id before logging

    owner_id = _get_owner_id_for_vehicle(db, data.vehicle_id)
    _create_log(db, owner_id, driver.id, data.vehicle_id, entry.id, "CREATE", None, _entry_snapshot(entry))

    db.commit()
    db.refresh(entry)
    return entry


# ── US-011: Driver views fuel entry history ───────────────────────────────────

def list_driver_fuel_entries(db: Session, driver_id: int) -> list[FuelEntry]:
    return (
        db.query(FuelEntry)
        .filter(FuelEntry.driver_id == driver_id)
        .order_by(FuelEntry.created_at.desc())
        .limit(10)
        .all()
    )


# ── US-012: Edit a fuel entry (within 24h) ────────────────────────────────────

def update_fuel_entry(db: Session, driver: User, entry_id: int, data: FuelEntryUpdate) -> FuelEntry:
    entry = db.query(FuelEntry).filter(
        FuelEntry.id == entry_id,
        FuelEntry.driver_id == driver.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée carburant introuvable")

    age = datetime.now(timezone.utc) - entry.created_at.replace(tzinfo=timezone.utc)
    if age > timedelta(hours=24):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette entrée ne peut plus être modifiée (délai de 24h dépassé)",
        )

    snapshot_before = _entry_snapshot(entry)
    updates = data.model_dump(exclude_none=True)

    new_odometer = updates.get("odometer_km", entry.odometer_km)
    new_quantity = float(updates.get("quantity_litres", entry.quantity_litres))

    # Validate odometer against previous entry (excluding this one)
    previous_odometer = _get_previous_odometer(db, entry.vehicle_id, exclude_entry_id=entry.id)
    if new_odometer <= previous_odometer:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le kilométrage ({new_odometer} km) doit être supérieur au dernier relevé ({previous_odometer} km)",
        )

    for field, value in updates.items():
        setattr(entry, field, value)

    distance_km, consumption = _compute_derived(new_quantity, new_odometer, previous_odometer)
    entry.distance_km = distance_km
    entry.consumption_per_100km = consumption
    entry.updated_at = datetime.now(timezone.utc)

    owner_id = _get_owner_id_for_vehicle(db, entry.vehicle_id)
    db.flush()
    snapshot_after = _entry_snapshot(entry)
    _create_log(db, owner_id, driver.id, entry.vehicle_id, entry.id, "UPDATE", snapshot_before, snapshot_after)

    db.commit()
    db.refresh(entry)
    return entry


# ── US-013: Delete a fuel entry (within 24h) ─────────────────────────────────

def delete_fuel_entry(db: Session, driver: User, entry_id: int) -> None:
    entry = db.query(FuelEntry).filter(
        FuelEntry.id == entry_id,
        FuelEntry.driver_id == driver.id,
    ).first()
    if not entry:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrée carburant introuvable")

    age = datetime.now(timezone.utc) - entry.created_at.replace(tzinfo=timezone.utc)
    if age > timedelta(hours=24):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette entrée ne peut plus être supprimée (délai de 24h dépassé)",
        )

    snapshot = _entry_snapshot(entry)
    owner_id = _get_owner_id_for_vehicle(db, entry.vehicle_id)
    vehicle_id = entry.vehicle_id

    # Log with NULL fuel_entry_id (entry about to be deleted)
    _create_log(db, owner_id, driver.id, vehicle_id, None, "DELETE", snapshot, None)

    db.delete(entry)
    db.commit()


# ── US-014: Owner views fleet fuel entries ────────────────────────────────────

def list_owner_fuel_entries(db: Session, owner_id: int) -> list[FuelEntry]:
    vehicle_ids = [
        v.id for v in db.query(Vehicle).filter(Vehicle.owner_id == owner_id).all()
    ]
    if not vehicle_ids:
        return []
    return (
        db.query(FuelEntry)
        .filter(FuelEntry.vehicle_id.in_(vehicle_ids))
        .order_by(FuelEntry.date.desc(), FuelEntry.created_at.desc())
        .all()
    )


# ── US-024: Owner views activity log ─────────────────────────────────────────

def list_activity_logs(db: Session, owner_id: int) -> list[ActivityLog]:
    return (
        db.query(ActivityLog)
        .filter(ActivityLog.owner_id == owner_id)
        .order_by(ActivityLog.created_at.desc())
        .all()
    )
