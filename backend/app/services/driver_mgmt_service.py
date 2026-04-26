from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.vehicle_driver import VehicleDriver
from app.core.security import hash_password


def _get_own_driver_or_404(db: Session, owner_id: int, driver_id: int) -> User:
    driver = db.get(User, driver_id)
    if not driver or driver.role != "DRIVER" or driver.owner_id != owner_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Chauffeur introuvable"
        )
    return driver


# ── US-047 ────────────────────────────────────────────────────────────────────


def create_driver(
    db: Session, owner_id: int, full_name: str, username: str, password: str
) -> User:
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce nom d'utilisateur est déjà utilisé",
        )

    driver = User(
        full_name=full_name,
        username=username,
        email=None,
        password_hash=hash_password(password),
        role="DRIVER",
        owner_id=owner_id,
        is_verified=True,  # no email verification step for drivers
        is_active=True,
        is_disabled=False,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def list_drivers(db: Session, owner_id: int) -> list[User]:
    return (
        db.query(User)
        .filter(User.owner_id == owner_id, User.role == "DRIVER")
        .order_by(User.full_name)
        .all()
    )


# ── US-048 ────────────────────────────────────────────────────────────────────


def set_driver_status(
    db: Session, owner_id: int, driver_id: int, is_disabled: bool
) -> User:
    driver = _get_own_driver_or_404(db, owner_id, driver_id)
    driver.is_disabled = is_disabled
    if is_disabled:
        # Force-deactivate driving session when disabled
        driver.driving_status = False
        driver.active_vehicle_id = None
    db.commit()
    db.refresh(driver)
    return driver


def reset_driver_password(
    db: Session, owner_id: int, driver_id: int, new_password: str
) -> None:
    driver = _get_own_driver_or_404(db, owner_id, driver_id)
    driver.password_hash = hash_password(new_password)
    db.commit()


def remove_driver(db: Session, owner_id: int, driver_id: int) -> None:
    driver = _get_own_driver_or_404(db, owner_id, driver_id)

    # Clear all vehicle assignments
    db.query(VehicleDriver).filter(VehicleDriver.driver_id == driver_id).delete()

    # Reset driving session
    driver.driving_status = False
    driver.active_vehicle_id = None
    db.commit()

    # Preserve fuel entries + activity logs — only delete the user record
    db.delete(driver)
    db.commit()
