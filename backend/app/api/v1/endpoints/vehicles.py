from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleUpdate,
    VehicleResponse,
    DriverSummary,
    AssignDriverRequest,
)
from app.services import vehicle_service

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


# ── List & detail ─────────────────────────────────────────────────────────────

@router.get("", response_model=None)
def list_vehicles(owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicles = vehicle_service.get_active_vehicles(db, owner.id)
    return _ok(data=[VehicleResponse.model_validate(v) for v in vehicles])


@router.get("/archived", response_model=None)
def list_archived(owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicles = vehicle_service.get_archived_vehicles(db, owner.id)
    return _ok(data=[VehicleResponse.model_validate(v) for v in vehicles])


@router.get("/{vehicle_id}", response_model=None)
def get_vehicle(vehicle_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.get_vehicle(db, owner.id, vehicle_id)
    return _ok(data=VehicleResponse.model_validate(vehicle))


# ── Create ────────────────────────────────────────────────────────────────────

@router.post("", status_code=status.HTTP_201_CREATED, response_model=None)
def create_vehicle(body: VehicleCreate, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.create_vehicle(db, owner.id, body)
    return _ok(data=VehicleResponse.model_validate(vehicle), message="Véhicule créé avec succès")


# ── Update ────────────────────────────────────────────────────────────────────

@router.patch("/{vehicle_id}", response_model=None)
def update_vehicle(vehicle_id: int, body: VehicleUpdate, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.update_vehicle(db, owner.id, vehicle_id, body)
    return _ok(data=VehicleResponse.model_validate(vehicle), message="Véhicule mis à jour")


# ── Status transitions ────────────────────────────────────────────────────────

@router.post("/{vehicle_id}/pause", response_model=None)
def pause_vehicle(vehicle_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.pause_vehicle(db, owner.id, vehicle_id)
    return _ok(data=VehicleResponse.model_validate(vehicle), message="Véhicule mis en pause")


@router.post("/{vehicle_id}/resume", response_model=None)
def resume_vehicle(vehicle_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.resume_vehicle(db, owner.id, vehicle_id)
    return _ok(data=VehicleResponse.model_validate(vehicle), message="Véhicule relancé")


@router.post("/{vehicle_id}/archive", response_model=None)
def archive_vehicle(vehicle_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.archive_vehicle(db, owner.id, vehicle_id)
    return _ok(data=VehicleResponse.model_validate(vehicle), message="Véhicule archivé")


@router.post("/{vehicle_id}/restore", response_model=None)
def restore_vehicle(vehicle_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle = vehicle_service.restore_vehicle(db, owner.id, vehicle_id)
    return _ok(data=VehicleResponse.model_validate(vehicle), message="Véhicule restauré")


# ── Driver assignment ─────────────────────────────────────────────────────────

@router.get("/{vehicle_id}/drivers", response_model=None)
def list_vehicle_drivers(vehicle_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    drivers = vehicle_service.get_vehicle_drivers(db, owner.id, vehicle_id)
    return _ok(data=[DriverSummary.model_validate(d) for d in drivers])


@router.post("/{vehicle_id}/drivers", status_code=status.HTTP_201_CREATED, response_model=None)
def assign_driver(vehicle_id: int, body: AssignDriverRequest, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle_service.assign_driver(db, owner.id, vehicle_id, body.driver_id)
    return _ok(message="Chauffeur assigné avec succès")


@router.delete("/{vehicle_id}/drivers/{driver_id}", status_code=status.HTTP_200_OK, response_model=None)
def remove_driver(vehicle_id: int, driver_id: int, owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    vehicle_service.remove_driver(db, owner.id, vehicle_id, driver_id)
    return _ok(message="Chauffeur retiré du véhicule")
