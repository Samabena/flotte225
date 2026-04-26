from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.driver_mgmt import (
    DriverCreate,
    DriverStatusUpdate,
    DriverPasswordReset,
    DriverResponse,
)
from app.services import driver_mgmt_service

router = APIRouter(prefix="/drivers", tags=["drivers"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_driver(
    body: DriverCreate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    driver = driver_mgmt_service.create_driver(
        db, owner.id, body.full_name, body.username, body.password
    )
    return _ok(
        data=DriverResponse.model_validate(driver).model_dump(),
        message="Chauffeur créé avec succès.",
    )


@router.get("", response_model=list[DriverResponse])
def list_drivers(
    owner: User = Depends(get_current_owner), db: Session = Depends(get_db)
):
    return driver_mgmt_service.list_drivers(db, owner.id)


@router.patch("/{driver_id}/status")
def set_driver_status(
    driver_id: int,
    body: DriverStatusUpdate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    driver = driver_mgmt_service.set_driver_status(
        db, owner.id, driver_id, body.is_disabled
    )
    action = "désactivé" if body.is_disabled else "réactivé"
    return _ok(
        data=DriverResponse.model_validate(driver).model_dump(),
        message=f"Chauffeur {action} avec succès.",
    )


@router.patch("/{driver_id}/password")
def reset_driver_password(
    driver_id: int,
    body: DriverPasswordReset,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    driver_mgmt_service.reset_driver_password(
        db, owner.id, driver_id, body.new_password
    )
    return _ok(message="Mot de passe réinitialisé avec succès.")


@router.delete("/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_driver(
    driver_id: int,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    driver_mgmt_service.remove_driver(db, owner.id, driver_id)
