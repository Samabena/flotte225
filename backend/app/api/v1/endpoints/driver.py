from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_driver
from app.models.user import User
from app.schemas.vehicle import (
    ActivateRequest,
    DeactivateRequest,
    VehicleResponse,
    DriverSummary,
)
from app.schemas.maintenance_expense import (
    MaintenanceExpenseCreate,
    MaintenanceExpenseResponse,
)
from app.schemas.revenue import RevenueCreate, RevenueResponse
from app.services import (
    vehicle_service,
    maintenance_expense_service,
    revenue_service,
)

router = APIRouter(prefix="/driver", tags=["driver"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


# ── US-022: View assigned vehicles ────────────────────────────────────────────


@router.get("/vehicles", response_model=None)
def my_vehicles(
    driver: User = Depends(get_current_driver), db: Session = Depends(get_db)
):
    vehicles = vehicle_service.get_driver_vehicles(db, driver.id)
    return _ok(data=[VehicleResponse.model_validate(v) for v in vehicles])


# ── US-023: Activate driving status ──────────────────────────────────────────


@router.post("/activate", response_model=None)
def activate(
    body: ActivateRequest,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    updated = vehicle_service.activate_driver(
        db, driver, body.vehicle_id, body.start_odometer, body.client_uuid
    )
    return _ok(
        data=DriverSummary.model_validate(updated),
        message="Statut activé — vous êtes en mission",
    )


@router.post("/deactivate", response_model=None)
def deactivate(
    body: DeactivateRequest | None = None,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    end_odometer = body.end_odometer if body else None
    updated = vehicle_service.deactivate_driver(db, driver, end_odometer)
    return _ok(
        data=DriverSummary.model_validate(updated),
        message="Statut désactivé",
    )


# ── Driver-logged maintenance expenses (for assigned vehicles) ────────────────


@router.post("/vehicles/{vehicle_id}/maintenance-expenses", response_model=None)
def driver_create_expense(
    vehicle_id: int,
    body: MaintenanceExpenseCreate,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    expense = maintenance_expense_service.create_expense_as_driver(
        db, driver, vehicle_id, body
    )
    return _ok(
        data=MaintenanceExpenseResponse.model_validate(expense),
        message="Dépense enregistrée",
    )


@router.get("/vehicles/{vehicle_id}/maintenance-expenses", response_model=None)
def driver_list_expenses(
    vehicle_id: int,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    expenses = maintenance_expense_service.list_vehicle_expenses_as_driver(
        db, driver, vehicle_id
    )
    return _ok(
        data=[MaintenanceExpenseResponse.model_validate(e) for e in expenses]
    )


# ── Driver-logged revenues (for assigned vehicles) ────────────────────────────


@router.post("/vehicles/{vehicle_id}/revenues", response_model=None)
def driver_create_revenue(
    vehicle_id: int,
    body: RevenueCreate,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    rev = revenue_service.create_revenue_as_driver(db, driver, vehicle_id, body)
    return _ok(data=RevenueResponse.model_validate(rev), message="Recette enregistrée")


@router.get("/vehicles/{vehicle_id}/revenues", response_model=None)
def driver_list_revenues(
    vehicle_id: int,
    driver: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    revs = revenue_service.list_vehicle_revenues_as_driver(db, driver, vehicle_id)
    return _ok(data=[RevenueResponse.model_validate(r) for r in revs])
