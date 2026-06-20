from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.revenue import RevenueCreate, RevenueResponse
from app.services import revenue_service

router = APIRouter(tags=["revenues"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


@router.post("/vehicles/{vehicle_id}/revenues", response_model=None)
def create_revenue(
    vehicle_id: int,
    body: RevenueCreate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    rev = revenue_service.create_revenue(db, owner.id, vehicle_id, body)
    return _ok(data=RevenueResponse.model_validate(rev), message="Recette enregistrée")


@router.get("/owner/revenues", response_model=None)
def list_revenues(
    vehicle_id: int | None = None,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    revs = revenue_service.list_owner_revenues(db, owner.id, vehicle_id)
    return _ok(data=[RevenueResponse.model_validate(r) for r in revs])


@router.delete("/revenues/{revenue_id}", response_model=None)
def delete_revenue(
    revenue_id: int,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    revenue_service.delete_revenue(db, owner.id, revenue_id)
    return _ok(message="Recette supprimée")
