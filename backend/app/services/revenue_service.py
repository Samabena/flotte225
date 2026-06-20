"""Revenue journal — per-vehicle income lines, entered by owner or driver.

Owner access via vehicle ownership; driver access via vehicle assignment.
Idempotent on client_uuid for offline sync.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.revenue import Revenue
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.schemas.revenue import RevenueCreate


def _owner_vehicle_or_404(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == vehicle_id, Vehicle.owner_id == owner_id)
        .first()
    )
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Véhicule introuvable"
        )
    return vehicle


def _assigned_or_403(db: Session, driver_id: int, vehicle_id: int) -> None:
    assignment = (
        db.query(VehicleDriver)
        .filter(
            VehicleDriver.driver_id == driver_id,
            VehicleDriver.vehicle_id == vehicle_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce véhicule",
        )


def _persist(
    db: Session, vehicle_id: int, driver_id: int | None, data: RevenueCreate
) -> Revenue:
    """Create the revenue row. Idempotent on client_uuid. Caller authorizes."""
    if data.client_uuid:
        existing = (
            db.query(Revenue).filter(Revenue.client_uuid == data.client_uuid).first()
        )
        if existing:
            return existing

    revenue = Revenue(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        date=data.date,
        amount_fcfa=data.amount_fcfa,
        note=data.note,
        client_uuid=data.client_uuid,
    )
    db.add(revenue)
    db.commit()
    db.refresh(revenue)
    return revenue


# ── Owner ──────────────────────────────────────────────────────────────────────


def create_revenue(
    db: Session, owner_id: int, vehicle_id: int, data: RevenueCreate
) -> Revenue:
    _owner_vehicle_or_404(db, owner_id, vehicle_id)
    return _persist(db, vehicle_id, None, data)


def list_owner_revenues(
    db: Session, owner_id: int, vehicle_id: int | None = None
) -> list[Revenue]:
    q = (
        db.query(Revenue)
        .join(Vehicle, Revenue.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
    )
    if vehicle_id is not None:
        q = q.filter(Revenue.vehicle_id == vehicle_id)
    return q.order_by(Revenue.date.desc(), Revenue.id.desc()).all()


def total_for_owner(db: Session, owner_id: int) -> float:
    total = (
        db.query(func.coalesce(func.sum(Revenue.amount_fcfa), 0))
        .join(Vehicle, Revenue.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
        .scalar()
    )
    return float(total or 0)


def delete_revenue(db: Session, owner_id: int, revenue_id: int) -> None:
    revenue = (
        db.query(Revenue)
        .join(Vehicle, Revenue.vehicle_id == Vehicle.id)
        .filter(Revenue.id == revenue_id, Vehicle.owner_id == owner_id)
        .first()
    )
    if not revenue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Recette introuvable"
        )
    db.delete(revenue)
    db.commit()


# ── Driver ─────────────────────────────────────────────────────────────────────


def create_revenue_as_driver(
    db: Session, driver: User, vehicle_id: int, data: RevenueCreate
) -> Revenue:
    _assigned_or_403(db, driver.id, vehicle_id)
    return _persist(db, vehicle_id, driver.id, data)


def list_vehicle_revenues_as_driver(
    db: Session, driver: User, vehicle_id: int
) -> list[Revenue]:
    _assigned_or_403(db, driver.id, vehicle_id)
    return (
        db.query(Revenue)
        .filter(Revenue.vehicle_id == vehicle_id)
        .order_by(Revenue.date.desc(), Revenue.id.desc())
        .all()
    )
