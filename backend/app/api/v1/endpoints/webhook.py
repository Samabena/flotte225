"""
Webhook endpoint — Sprint 8
  US-029  POST /webhook/trigger  — Manually trigger webhook dispatch
  US-030  GET  /webhook/status   — Last dispatch timestamp + HTTP status
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.webhook import WebhookStatusResponse
from app.services import webhook_service

router = APIRouter(prefix="/webhook", tags=["webhook"])


@router.get("/status", response_model=WebhookStatusResponse)
def get_webhook_status(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-030 — Return last webhook dispatch timestamp and HTTP status."""
    state = webhook_service.get_webhook_status(db, owner.id)
    return WebhookStatusResponse(
        configured=bool(settings.WEBHOOK_URL),
        last_sent_at=state.last_sent_at if state else None,
        last_status_code=state.last_status_code if state else None,
    )


@router.post("/trigger", response_model=WebhookStatusResponse)
def trigger_webhook(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-029 — Manually trigger a webhook dispatch for this owner."""
    try:
        state = webhook_service.trigger_webhook(db, owner.id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    return WebhookStatusResponse(
        configured=True,
        last_sent_at=state.last_sent_at,
        last_status_code=state.last_status_code,
    )
