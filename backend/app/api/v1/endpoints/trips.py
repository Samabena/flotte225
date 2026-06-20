from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.trip import TripResponse
from app.services import trip_service

router = APIRouter(tags=["trips"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


@router.get("/owner/trips", response_model=None)
def list_trips(
    vehicle_id: int | None = None,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """List driving sessions (trip logs) across the owner's fleet."""
    trips = trip_service.list_owner_trips(db, owner.id, vehicle_id)
    return _ok(data=[TripResponse.model_validate(t) for t in trips])
