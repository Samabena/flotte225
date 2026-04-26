from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.maintenance import Maintenance
from app.models.vehicle import Vehicle
from app.schemas.maintenance import MaintenanceUpdate


def _get_vehicle_or_404(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = (
        db.query(Vehicle)
        .filter(
            Vehicle.id == vehicle_id,
            Vehicle.owner_id == owner_id,
        )
        .first()
    )
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Véhicule introuvable"
        )
    return vehicle


def _get_or_create_record(db: Session, vehicle_id: int) -> Maintenance:
    record = db.query(Maintenance).filter(Maintenance.vehicle_id == vehicle_id).first()
    if not record:
        record = Maintenance(vehicle_id=vehicle_id)
        db.add(record)
        db.commit()
        db.refresh(record)
    return record


# ── US-015: Get maintenance record ────────────────────────────────────────────


def get_maintenance(db: Session, owner_id: int, vehicle_id: int) -> Maintenance:
    _get_vehicle_or_404(db, owner_id, vehicle_id)
    return _get_or_create_record(db, vehicle_id)


# ── US-015: Update maintenance record ────────────────────────────────────────


def update_maintenance(
    db: Session, owner_id: int, vehicle_id: int, data: MaintenanceUpdate
) -> Maintenance:
    _get_vehicle_or_404(db, owner_id, vehicle_id)
    record = _get_or_create_record(db, vehicle_id)

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(record, field, value)

    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record
