from fastapi import APIRouter, Depends
from app.core.config import settings
from app.core.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/maps")
def get_maps_config(current_user: User = Depends(get_current_user)):
    """Return the Google Maps API key for authenticated users."""
    return {"google_maps_api_key": settings.GOOGLE_MAPS_API_KEY}
