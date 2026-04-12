"""
Webhook Service — Sprint 8
  US-029  Automated webhook dispatch every N hours
  US-030  View last webhook status

Silently disabled if WEBHOOK_URL env var is not set.
Payload: fleet summary snapshot delivered to the configured endpoint.
"""
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.webhook_state import WebhookState

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


# ── Public API ────────────────────────────────────────────────────────────────

def get_webhook_status(db: Session, owner_id: int) -> WebhookState | None:
    """Return the owner's webhook state record, or None if never dispatched."""
    return db.query(WebhookState).filter(WebhookState.owner_id == owner_id).first()


def trigger_webhook(db: Session, owner_id: int) -> WebhookState:
    """
    Manually dispatch the webhook for this owner.
    Raises ValueError if WEBHOOK_URL is not configured.
    """
    if not settings.WEBHOOK_URL:
        raise ValueError("WEBHOOK_URL n'est pas configuré sur ce serveur.")

    payload = _build_payload(db, owner_id)
    status_code = _dispatch(payload)

    state = _get_or_create_state(db, owner_id)
    state.last_sent_at = datetime.now(timezone.utc)
    state.last_status_code = status_code
    state.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(state)
    return state


def run_webhook_dispatch(db: Session) -> None:
    """
    Called by APScheduler every WEBHOOK_INTERVAL_HOURS.
    Dispatches for all active owners if WEBHOOK_URL is set.
    """
    if not settings.WEBHOOK_URL:
        return

    from app.models.user import User

    owners = (
        db.query(User)
        .filter(User.role == "OWNER", User.is_active == True)
        .all()
    )
    for owner in owners:
        try:
            payload = _build_payload(db, owner.id)
            status_code = _dispatch(payload)

            state = _get_or_create_state(db, owner.id)
            state.last_sent_at = datetime.now(timezone.utc)
            state.last_status_code = status_code
            state.updated_at = datetime.now(timezone.utc)
            db.commit()
        except Exception as exc:
            logger.error("Webhook dispatch failed for owner %s: %s", owner.id, exc)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_or_create_state(db: Session, owner_id: int) -> WebhookState:
    state = db.query(WebhookState).filter(WebhookState.owner_id == owner_id).first()
    if not state:
        state = WebhookState(owner_id=owner_id)
        db.add(state)
        db.commit()
        db.refresh(state)
    return state


def _build_payload(db: Session, owner_id: int) -> dict:
    """Build the fleet summary payload for the webhook."""
    from sqlalchemy import func
    from app.models.fuel_entry import FuelEntry
    from app.models.user import User
    from app.models.vehicle import Vehicle
    from app.services.alert_service import compute_alerts

    owner = db.get(User, owner_id)
    vehicles = db.query(Vehicle).filter(
        Vehicle.owner_id == owner_id,
        Vehicle.status != "archived",
    ).all()

    vehicle_ids = [v.id for v in vehicles]
    total_spend = 0.0
    if vehicle_ids:
        total_spend = (
            db.query(func.coalesce(func.sum(FuelEntry.amount_fcfa), 0))
            .filter(FuelEntry.vehicle_id.in_(vehicle_ids))
            .scalar() or 0
        )

    alerts = compute_alerts(db, owner_id)
    critical_count = sum(1 for a in alerts if a.severity == "critical")
    warning_count = sum(1 for a in alerts if a.severity == "warning")

    return {
        "event": "fleet_summary",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "owner": {
            "id": owner_id,
            "name": owner.full_name if owner else "",
            "email": owner.email if owner else "",
        },
        "fleet": {
            "active_vehicles": len(vehicles),
            "total_fuel_spend_fcfa": float(total_spend),
        },
        "alerts": {
            "critical": critical_count,
            "warning": warning_count,
        },
    }


def _dispatch(payload: dict) -> int:
    """POST payload to WEBHOOK_URL. Returns HTTP status code."""
    try:
        response = httpx.post(
            settings.WEBHOOK_URL,
            json=payload,
            timeout=_TIMEOUT,
        )
        if response.status_code >= 400:
            logger.warning("Webhook endpoint returned %s", response.status_code)
        return response.status_code
    except httpx.TimeoutException:
        logger.error("Webhook dispatch timed out to %s", settings.WEBHOOK_URL)
        return 0
    except Exception as exc:
        logger.error("Webhook dispatch error: %s", exc)
        return 0
