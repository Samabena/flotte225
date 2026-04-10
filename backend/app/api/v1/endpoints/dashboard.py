from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services import dashboard_service

router = APIRouter(tags=["dashboard"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


@router.get("/dashboard/owner", response_model=None)
def owner_dashboard(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """
    US-017 Fleet financial summary & charts
    US-018 Fleet consumption indicators
    US-019 Driver status panel
    US-020 Alerts, anomalies & compliance on dashboard
    """
    data = dashboard_service.get_dashboard_data(db, owner.id)
    return _ok(data=DashboardResponse.model_validate(data))
