"""Trip logging — captures odometer when a driver takes (start) and returns
(end) a vehicle. Tied to the driver activate/deactivate flow."""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.models.trip_log import TripLog
from app.models.user import User
from app.models.vehicle import Vehicle


def last_known_odometer(db: Session, vehicle_id: int) -> int:
    """Highest odometer ever recorded for a vehicle, across its initial
    mileage, fuel entries and completed trips."""
    vehicle = db.get(Vehicle, vehicle_id)
    candidates: list[int] = [vehicle.initial_mileage] if vehicle else [0]

    fuel_max = (
        db.query(func.max(FuelEntry.odometer_km))
        .filter(FuelEntry.vehicle_id == vehicle_id)
        .scalar()
    )
    if fuel_max is not None:
        candidates.append(int(fuel_max))

    trip_max = (
        db.query(func.max(TripLog.end_odometer))
        .filter(TripLog.vehicle_id == vehicle_id)
        .scalar()
    )
    if trip_max is not None:
        candidates.append(int(trip_max))

    return max(candidates)


def _open_trip_for_driver(db: Session, driver_id: int) -> TripLog | None:
    return (
        db.query(TripLog)
        .filter(TripLog.driver_id == driver_id, TripLog.ended_at.is_(None))
        .order_by(TripLog.started_at.desc())
        .first()
    )


def start_trip(
    db: Session,
    driver: User,
    vehicle_id: int,
    start_odometer: int,
    client_uuid: str | None = None,
) -> TripLog:
    """Open a trip. Idempotent on client_uuid (returns the existing one)."""
    if client_uuid:
        existing = (
            db.query(TripLog).filter(TripLog.client_uuid == client_uuid).first()
        )
        if existing:
            return existing

    floor = last_known_odometer(db, vehicle_id)
    if start_odometer < floor:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le kilométrage de départ ({start_odometer}) ne peut pas être "
            f"inférieur au dernier relevé connu ({floor}).",
        )

    # Defensively close any dangling open trip for this driver
    dangling = _open_trip_for_driver(db, driver.id)
    if dangling:
        dangling.ended_at = datetime.now(timezone.utc)

    trip = TripLog(
        vehicle_id=vehicle_id,
        driver_id=driver.id,
        start_odometer=start_odometer,
        started_at=datetime.now(timezone.utc),
        client_uuid=client_uuid,
    )
    db.add(trip)
    db.flush()
    return trip


def end_trip(db: Session, driver: User, end_odometer: int) -> TripLog | None:
    """Close the driver's open trip with the return odometer."""
    trip = _open_trip_for_driver(db, driver.id)
    if trip is None:
        return None

    if end_odometer < trip.start_odometer:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Le kilométrage de retour ({end_odometer}) ne peut pas être "
            f"inférieur au kilométrage de départ ({trip.start_odometer}).",
        )

    trip.end_odometer = end_odometer
    trip.distance_km = end_odometer - trip.start_odometer
    trip.ended_at = datetime.now(timezone.utc)
    db.flush()
    return trip


def list_owner_trips(
    db: Session, owner_id: int, vehicle_id: int | None = None
) -> list[TripLog]:
    q = (
        db.query(TripLog)
        .join(Vehicle, TripLog.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
    )
    if vehicle_id is not None:
        q = q.filter(TripLog.vehicle_id == vehicle_id)
    return q.order_by(TripLog.started_at.desc()).all()
