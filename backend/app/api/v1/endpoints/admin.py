"""
Admin & subscription endpoints — Sprint 6 + 7
  US-036  GET  /admin/users
  US-037  PATCH /admin/users/{id}/suspend | /reactivate
  US-038  DELETE /admin/users/{id}
  US-039  GET  /admin/users/{id}/fleet
  US-040  PUT  /admin/users/{id}/plan
  US-041  GET  /admin/analytics
  US-034  PATCH /owner/whatsapp
  US-046  GET  /subscription/my-plan
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_admin_user, get_current_owner
from app.models.user import User
from app.schemas.admin import AssignPlanRequest, UserSummary
from app.services import admin_service, analytics_service

router = APIRouter(tags=["admin"])


def _ok(data=None, message: str = ""):
    return {"success": True, "data": data, "message": message}


# ── US-036: List / search all users ──────────────────────────────────────────

@router.get("/admin/users", response_model=None)
def list_users(
    q: Annotated[str | None, Query(description="Recherche par nom ou email")] = None,
    role: Annotated[str | None, Query(description="Filtrer par rôle : OWNER | DRIVER | SUPER_ADMIN")] = None,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-036 — View & search all users (super admin only)."""
    users = admin_service.list_users(db, q=q, role=role)
    return _ok(data=[UserSummary.model_validate(u) for u in users])


# ── US-037: Suspend / reactivate ──────────────────────────────────────────────

@router.patch("/admin/users/{user_id}/suspend", response_model=None)
def suspend_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-037 — Suspend a user account."""
    user = admin_service.suspend_user(db, admin, user_id)
    return _ok(data=UserSummary.model_validate(user), message="Compte suspendu")


@router.patch("/admin/users/{user_id}/reactivate", response_model=None)
def reactivate_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-037 — Reactivate a suspended user account."""
    user = admin_service.reactivate_user(db, admin, user_id)
    return _ok(data=UserSummary.model_validate(user), message="Compte réactivé")


# ── US-038: Permanently delete ────────────────────────────────────────────────

@router.delete("/admin/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-038 — Permanently delete a user and all associated data."""
    admin_service.delete_user(db, admin, user_id)


# ── US-039: View any owner's fleet ───────────────────────────────────────────

@router.get("/admin/users/{user_id}/fleet", response_model=None)
def get_owner_fleet(
    user_id: int,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-039 — View any owner's complete fleet (super admin only)."""
    fleet = admin_service.get_owner_fleet(db, user_id)
    return _ok(data=fleet)


# ── US-040: Assign / change subscription plan ────────────────────────────────

@router.put("/admin/users/{user_id}/plan", response_model=None)
def assign_plan(
    user_id: int,
    body: AssignPlanRequest,
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-040 — Assign or change a subscription plan for an owner."""
    admin_service.assign_plan(db, admin, user_id, body)
    return _ok(message="Plan mis à jour avec succès")


# ── US-046: Owner views current plan & usage ─────────────────────────────────

@router.get("/subscription/my-plan", response_model=None)
def my_plan(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-046 — Owner views their current plan and resource usage."""
    data = admin_service.get_plan_usage(db, owner.id)
    return _ok(data=data)


# ── US-041: Platform-wide analytics ──────────────────────────────────────────

@router.get("/admin/analytics", response_model=None)
def platform_analytics(
    admin: User = Depends(get_admin_user),
    db: Session = Depends(get_db),
):
    """US-041 — Platform-wide analytics (super admin only)."""
    data = analytics_service.get_platform_analytics(db)
    return _ok(data=data)


# ── US-034: Configure WhatsApp number ────────────────────────────────────────

class WhatsAppConfigRequest(BaseModel):
    whatsapp_number: str


@router.patch("/owner/whatsapp", response_model=None)
def configure_whatsapp(
    body: WhatsAppConfigRequest,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-034 — Owner sets or updates their WhatsApp number for fleet alerts."""
    owner.whatsapp_number = body.whatsapp_number.strip() or None
    db.commit()
    return _ok(message="Numéro WhatsApp mis à jour")
