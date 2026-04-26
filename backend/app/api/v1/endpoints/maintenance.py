from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.maintenance import MaintenanceUpdate, MaintenanceResponse
from app.schemas.alert import AlertResponse
from app.services import maintenance_service, alert_service

router = APIRouter(tags=["maintenance"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


# ── US-015: Maintenance record ────────────────────────────────────────────────


@router.get("/vehicles/{vehicle_id}/maintenance", response_model=None)
def get_maintenance(
    vehicle_id: int,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-015 — Get maintenance record (auto-creates if missing)."""
    record = maintenance_service.get_maintenance(db, owner.id, vehicle_id)
    return _ok(data=MaintenanceResponse.model_validate(record))


@router.put("/vehicles/{vehicle_id}/maintenance", response_model=None)
def update_maintenance(
    vehicle_id: int,
    body: MaintenanceUpdate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-015 — Update maintenance record."""
    record = maintenance_service.update_maintenance(db, owner.id, vehicle_id, body)
    return _ok(
        data=MaintenanceResponse.model_validate(record),
        message="Maintenance mise à jour",
    )


# ── US-026/027/028: Alert engine ──────────────────────────────────────────────


@router.get("/owner/alerts", response_model=None)
def get_alerts(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-026/027/028 — Compute and return all active alerts for the fleet."""
    alerts = alert_service.compute_alerts(db, owner.id)
    return _ok(data=[AlertResponse.model_validate(a) for a in alerts])
