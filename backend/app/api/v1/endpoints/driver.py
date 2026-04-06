from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_driver
from app.models.user import User
from app.schemas.vehicle import ActivateRequest, VehicleResponse, DriverSummary
from app.services import vehicle_service

router = APIRouter(prefix="/driver", tags=["driver"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


# ── US-022: View assigned vehicles ────────────────────────────────────────────

@router.get("/vehicles", response_model=None)
def my_vehicles(driver: User = Depends(get_current_driver), db: Session = Depends(get_db)):
    vehicles = vehicle_service.get_driver_vehicles(db, driver.id)
    return _ok(data=[VehicleResponse.model_validate(v) for v in vehicles])


# ── US-023: Activate driving status ──────────────────────────────────────────

@router.post("/activate", response_model=None)
def activate(body: ActivateRequest, driver: User = Depends(get_current_driver), db: Session = Depends(get_db)):
    updated = vehicle_service.activate_driver(db, driver, body.vehicle_id)
    return _ok(
        data=DriverSummary.model_validate(updated),
        message="Statut activé — vous êtes en mission",
    )


@router.post("/deactivate", response_model=None)
def deactivate(driver: User = Depends(get_current_driver), db: Session = Depends(get_db)):
    updated = vehicle_service.deactivate_driver(db, driver)
    return _ok(
        data=DriverSummary.model_validate(updated),
        message="Statut désactivé",
    )
