"""
Admin & subscription service — Sprint 6
  US-036  View & search all users
  US-037  Suspend / reactivate a user
  US-038  Permanently delete a user
  US-039  View any owner's fleet
  US-040  Manage subscription plan per owner
  US-046  Owner views current plan & usage
"""
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.activity_log import ActivityLog
from app.models.fuel_entry import FuelEntry
from app.models.maintenance import Maintenance
from app.models.otp_code import OtpCode
from app.models.subscription import OwnerSubscription, SubscriptionPlan
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.schemas.admin import (
    AdminVehicleSummary,
    AssignPlanRequest,
    OwnerFleetResponse,
    PlanDetails,
    PlanUsageResponse,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Utilisateur introuvable")
    return user


def _get_plan_by_name(db: Session, plan_name: str) -> SubscriptionPlan:
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Plan inconnu : {plan_name}. Valeurs valides : starter, pro, business",
        )
    return plan


# ── US-036: List / search users ───────────────────────────────────────────────

def list_users(db: Session, q: str | None = None, role: str | None = None) -> list[User]:
    query = db.query(User)
    if role:
        query = query.filter(User.role == role.upper())
    if q:
        like = f"%{q}%"
        query = query.filter((User.email.ilike(like)) | (User.full_name.ilike(like)))
    return query.order_by(User.created_at.desc()).all()


# ── US-037: Suspend / reactivate ──────────────────────────────────────────────

def suspend_user(db: Session, admin: User, user_id: int) -> User:
    user = _get_user_or_404(db, user_id)
    if user.role == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de suspendre un super administrateur",
        )
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def reactivate_user(db: Session, admin: User, user_id: int) -> User:
    user = _get_user_or_404(db, user_id)
    if user.role == "SUPER_ADMIN":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Action non autorisée")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


# ── US-038: Permanently delete ────────────────────────────────────────────────

def delete_user(db: Session, admin: User, user_id: int) -> None:
    user = _get_user_or_404(db, user_id)
    if user.role == "SUPER_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de supprimer un super administrateur",
        )
    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Impossible de supprimer son propre compte",
        )

    # OTP codes (non-null FK user_id)
    db.query(OtpCode).filter(OtpCode.user_id == user_id).delete()

    if user.role == "OWNER":
        vehicle_ids = [
            row[0] for row in db.query(Vehicle.id).filter(Vehicle.owner_id == user_id).all()
        ]
        if vehicle_ids:
            # Activity logs reference vehicle_id (NOT NULL, no CASCADE)
            db.query(ActivityLog).filter(ActivityLog.vehicle_id.in_(vehicle_ids)).delete(
                synchronize_session=False
            )
            db.query(FuelEntry).filter(FuelEntry.vehicle_id.in_(vehicle_ids)).delete(
                synchronize_session=False
            )
            db.query(VehicleDriver).filter(VehicleDriver.vehicle_id.in_(vehicle_ids)).delete(
                synchronize_session=False
            )
            db.query(Maintenance).filter(Maintenance.vehicle_id.in_(vehicle_ids)).delete(
                synchronize_session=False
            )
            # Nullify active_vehicle_id for drivers still linked to these vehicles
            db.query(User).filter(User.active_vehicle_id.in_(vehicle_ids)).update(
                {"active_vehicle_id": None, "driving_status": False},
                synchronize_session=False,
            )
            db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).delete(
                synchronize_session=False
            )
        # Activity logs where owner_id = user_id (not covered by vehicle filter if fleet was empty)
        db.query(ActivityLog).filter(ActivityLog.owner_id == user_id).delete(
            synchronize_session=False
        )
        db.query(OwnerSubscription).filter(OwnerSubscription.owner_id == user_id).delete()

    elif user.role == "DRIVER":
        # Nullify the driver's active vehicle reference before deleting
        user.active_vehicle_id = None
        user.driving_status = False
        db.flush()
        db.query(ActivityLog).filter(ActivityLog.driver_id == user_id).delete()
        db.query(VehicleDriver).filter(VehicleDriver.driver_id == user_id).delete()

    db.delete(user)
    db.commit()


# ── US-039: View any owner's fleet ───────────────────────────────────────────

def get_owner_fleet(db: Session, owner_id: int) -> OwnerFleetResponse:
    owner = _get_user_or_404(db, owner_id)
    if owner.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur n'est pas un propriétaire de flotte",
        )
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.owner_id == owner_id)
        .order_by(Vehicle.created_at.desc())
        .all()
    )
    return OwnerFleetResponse(
        owner_id=owner.id,
        owner_name=owner.full_name,
        owner_email=owner.email,
        vehicles=[AdminVehicleSummary.model_validate(v) for v in vehicles],
    )


# ── US-040: Assign plan to owner ──────────────────────────────────────────────

def assign_plan(db: Session, admin: User, owner_id: int, body: AssignPlanRequest) -> None:
    owner = _get_user_or_404(db, owner_id)
    if owner.role != "OWNER":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cet utilisateur n'est pas un propriétaire de flotte",
        )
    plan = _get_plan_by_name(db, body.plan_name)

    sub = db.query(OwnerSubscription).filter(OwnerSubscription.owner_id == owner_id).first()
    if sub:
        sub.plan_id = plan.id
        sub.started_at = datetime.now(timezone.utc)
        sub.expires_at = body.expires_at
        sub.is_active = True
        sub.assigned_by = admin.id
    else:
        sub = OwnerSubscription(
            owner_id=owner_id,
            plan_id=plan.id,
            started_at=datetime.now(timezone.utc),
            expires_at=body.expires_at,
            is_active=True,
            assigned_by=admin.id,
        )
        db.add(sub)
    db.commit()


# ── US-046: Owner views plan + usage ─────────────────────────────────────────

def get_plan_usage(db: Session, owner_id: int) -> PlanUsageResponse:
    sub = (
        db.query(OwnerSubscription)
        .filter(OwnerSubscription.owner_id == owner_id, OwnerSubscription.is_active == True)
        .first()
    )
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Aucun abonnement actif"
        )
    plan = db.get(SubscriptionPlan, sub.plan_id)

    active_vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.owner_id == owner_id, Vehicle.status != "archived")
        .count()
    )
    active_drivers = (
        db.query(VehicleDriver.driver_id)
        .join(Vehicle, VehicleDriver.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id, Vehicle.status != "archived")
        .distinct()
        .count()
    )

    return PlanUsageResponse(
        plan=PlanDetails.model_validate(plan),
        active_vehicles=active_vehicles,
        active_drivers=active_drivers,
        expires_at=sub.expires_at,
    )
