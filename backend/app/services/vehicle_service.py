from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.models.user import User
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


# ── helpers ──────────────────────────────────────────────────────────────────


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


def _get_driver_or_400(db: Session, owner_id: int, driver_id: int) -> User:
    """Return driver only if they exist, have DRIVER role, and belong to this owner."""
    driver = db.get(User, driver_id)
    if not driver or driver.role != "DRIVER" or driver.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chauffeur introuvable ou non autorisé",
        )
    return driver


# ── US-005: Create vehicle ────────────────────────────────────────────────────


def create_vehicle(db: Session, owner_id: int, data: VehicleCreate) -> Vehicle:
    if db.query(Vehicle).filter(Vehicle.license_plate == data.license_plate).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce numéro de plaque existe déjà",
        )

    vehicle = Vehicle(
        owner_id=owner_id,
        name=data.name,
        brand=data.brand,
        model=data.model,
        year=data.year,
        license_plate=data.license_plate,
        vin=data.vin,
        fuel_type=data.fuel_type,
        initial_mileage=data.initial_mileage,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)

    if data.driver_ids:
        for driver_id in data.driver_ids:
            try:
                _do_assign_driver(db, owner_id, vehicle.id, driver_id)
            except HTTPException:
                pass  # skip invalid driver_ids silently on creation

    return vehicle


# ── US-006: Update vehicle ────────────────────────────────────────────────────


def update_vehicle(
    db: Session, owner_id: int, vehicle_id: int, data: VehicleUpdate
) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, owner_id, vehicle_id)

    if vehicle.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible de modifier un véhicule archivé",
        )

    updates = data.model_dump(exclude_none=True)

    if "license_plate" in updates and updates["license_plate"] != vehicle.license_plate:
        if (
            db.query(Vehicle)
            .filter(Vehicle.license_plate == updates["license_plate"])
            .first()
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ce numéro de plaque existe déjà",
            )

    for field, value in updates.items():
        setattr(vehicle, field, value)

    vehicle.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ── US-007: Pause / resume ────────────────────────────────────────────────────


def pause_vehicle(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, owner_id, vehicle_id)
    if vehicle.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul un véhicule actif peut être mis en pause",
        )
    vehicle.status = "paused"
    vehicle.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def resume_vehicle(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, owner_id, vehicle_id)
    if vehicle.status != "paused":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul un véhicule en pause peut être relancé",
        )
    vehicle.status = "active"
    vehicle.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ── US-008: Archive / restore ─────────────────────────────────────────────────


def archive_vehicle(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, owner_id, vehicle_id)
    if vehicle.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce véhicule est déjà archivé",
        )

    # Reset any active driver currently driving this vehicle
    active_driver = (
        db.query(User)
        .filter(
            User.active_vehicle_id == vehicle_id,
            User.driving_status.is_(True),
        )
        .first()
    )
    if active_driver:
        active_driver.driving_status = False
        active_driver.active_vehicle_id = None

    vehicle.status = "archived"
    vehicle.archived_at = datetime.now(timezone.utc)
    vehicle.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def restore_vehicle(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = _get_vehicle_or_404(db, owner_id, vehicle_id)
    if vehicle.status != "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul un véhicule archivé peut être restauré",
        )

    vehicle.status = "active"
    vehicle.archived_at = None
    vehicle.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(vehicle)
    return vehicle


# ── US-009: Assign / remove drivers ──────────────────────────────────────────


def _do_assign_driver(
    db: Session, owner_id: int, vehicle_id: int, driver_id: int
) -> None:
    vehicle = _get_vehicle_or_404(db, owner_id, vehicle_id)
    if vehicle.status == "archived":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Impossible d'assigner un chauffeur à un véhicule archivé",
        )

    _get_driver_or_400(db, owner_id, driver_id)

    existing = (
        db.query(VehicleDriver)
        .filter(
            VehicleDriver.vehicle_id == vehicle_id,
            VehicleDriver.driver_id == driver_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce chauffeur est déjà assigné à ce véhicule",
        )

    db.add(VehicleDriver(vehicle_id=vehicle_id, driver_id=driver_id))
    db.commit()


def assign_driver(db: Session, owner_id: int, vehicle_id: int, driver_id: int) -> None:
    _do_assign_driver(db, owner_id, vehicle_id, driver_id)


def remove_driver(db: Session, owner_id: int, vehicle_id: int, driver_id: int) -> None:
    _get_vehicle_or_404(db, owner_id, vehicle_id)

    assignment = (
        db.query(VehicleDriver)
        .filter(
            VehicleDriver.vehicle_id == vehicle_id,
            VehicleDriver.driver_id == driver_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce chauffeur n'est pas assigné à ce véhicule",
        )

    # Reset driving status if driver is currently active on this vehicle
    driver = db.get(User, driver_id)
    if driver and driver.driving_status and driver.active_vehicle_id == vehicle_id:
        driver.driving_status = False
        driver.active_vehicle_id = None

    db.delete(assignment)
    db.commit()


def get_vehicle_drivers(db: Session, owner_id: int, vehicle_id: int) -> list[User]:
    _get_vehicle_or_404(db, owner_id, vehicle_id)
    assignments = (
        db.query(VehicleDriver).filter(VehicleDriver.vehicle_id == vehicle_id).all()
    )
    driver_ids = [a.driver_id for a in assignments]
    return db.query(User).filter(User.id.in_(driver_ids)).all()


# ── List queries ──────────────────────────────────────────────────────────────


def get_active_vehicles(db: Session, owner_id: int) -> list[Vehicle]:
    return (
        db.query(Vehicle)
        .filter(Vehicle.owner_id == owner_id, Vehicle.status != "archived")
        .order_by(Vehicle.created_at.desc())
        .all()
    )


def get_archived_vehicles(db: Session, owner_id: int) -> list[Vehicle]:
    return (
        db.query(Vehicle)
        .filter(Vehicle.owner_id == owner_id, Vehicle.status == "archived")
        .order_by(Vehicle.archived_at.desc())
        .all()
    )


def get_vehicle(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    return _get_vehicle_or_404(db, owner_id, vehicle_id)


# ── US-022: Driver views assigned vehicles ────────────────────────────────────


def get_driver_vehicles(db: Session, driver_id: int) -> list[Vehicle]:
    assignments = (
        db.query(VehicleDriver).filter(VehicleDriver.driver_id == driver_id).all()
    )
    vehicle_ids = [a.vehicle_id for a in assignments]
    if not vehicle_ids:
        return []
    return (
        db.query(Vehicle)
        .filter(Vehicle.id.in_(vehicle_ids), Vehicle.status != "archived")
        .order_by(Vehicle.name)
        .all()
    )


# ── US-023: Toggle driving status ─────────────────────────────────────────────


def activate_driver(db: Session, driver: User, vehicle_id: int) -> User:
    # Verify driver is assigned to this vehicle
    assignment = (
        db.query(VehicleDriver)
        .filter(
            VehicleDriver.driver_id == driver.id,
            VehicleDriver.vehicle_id == vehicle_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce véhicule",
        )

    vehicle = db.get(Vehicle, vehicle_id)
    if not vehicle or vehicle.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce véhicule n'est pas disponible",
        )

    driver.driving_status = True
    driver.active_vehicle_id = vehicle_id
    db.commit()
    db.refresh(driver)
    return driver


def deactivate_driver(db: Session, driver: User) -> User:
    driver.driving_status = False
    driver.active_vehicle_id = None
    db.commit()
    db.refresh(driver)
    return driver
