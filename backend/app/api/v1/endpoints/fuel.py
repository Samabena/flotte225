from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_driver, get_current_owner
from app.models.user import User
from app.schemas.fuel_entry import FuelEntryCreate, FuelEntryUpdate, FuelEntryResponse
from app.schemas.activity_log import ActivityLogResponse
from app.services import fuel_service

router = APIRouter(tags=["fuel"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


# ── Driver endpoints ──────────────────────────────────────────────────────────

@router.post("/fuel", status_code=status.HTTP_201_CREATED, response_model=None)
def submit_fuel_entry(
    body: FuelEntryCreate,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """US-010 — Submit a fuel entry."""
    entry = fuel_service.create_fuel_entry(db, driver, body)
    return _ok(data=FuelEntryResponse.model_validate(entry), message="Entrée carburant enregistrée")


@router.get("/fuel", response_model=None)
def list_my_fuel_entries(
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """US-011 — View my last 10 fuel entries."""
    entries = fuel_service.list_driver_fuel_entries(db, driver.id)
    return _ok(data=[FuelEntryResponse.model_validate(e) for e in entries])


@router.patch("/fuel/{entry_id}", response_model=None)
def edit_fuel_entry(
    entry_id: int,
    body: FuelEntryUpdate,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """US-012 — Edit a fuel entry within 24h."""
    entry = fuel_service.update_fuel_entry(db, driver, entry_id, body)
    return _ok(data=FuelEntryResponse.model_validate(entry), message="Entrée carburant mise à jour")


@router.delete("/fuel/{entry_id}", status_code=status.HTTP_200_OK, response_model=None)
def delete_fuel_entry(
    entry_id: int,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """US-013 — Delete a fuel entry within 24h."""
    fuel_service.delete_fuel_entry(db, driver, entry_id)
    return _ok(message="Entrée carburant supprimée")


# ── Owner endpoints ───────────────────────────────────────────────────────────

@router.get("/owner/fuel-entries", response_model=None)
def list_fleet_fuel_entries(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-014 — Owner views all fleet fuel entries."""
    entries = fuel_service.list_owner_fuel_entries(db, owner.id)
    return _ok(data=[FuelEntryResponse.model_validate(e) for e in entries])


@router.get("/owner/activity-logs", response_model=None)
def list_fleet_activity_logs(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-024 — Owner views audit log."""
    logs = fuel_service.list_activity_logs(db, owner.id)
    return _ok(data=[ActivityLogResponse.model_validate(log) for log in logs])
