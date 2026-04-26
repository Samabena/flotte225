"""
Alert email service — instant + daily digest delivery.
  - process_instant_alert_emails: edge-detects new/upgraded alerts, sends per-alert email
  - send_daily_digest_emails: nightly summary of all unresolved alerts
"""
import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.alert_state import AlertState
from app.models.user import User
from app.services.alert_service import compute_alerts
from app.services.email_service import (
    build_daily_digest_email,
    build_instant_alert_email,
    send_email,
)

logger = logging.getLogger(__name__)


def _active_owners(db: Session):
    return (
        db.query(User)
        .filter(
            User.role == "OWNER",
            User.is_active.is_(True),
            User.email.isnot(None),
            User.email_alerts_enabled.is_(True),
        )
        .all()
    )


def _send_instant(owner: User, alert) -> None:
    try:
        subject, html = build_instant_alert_email(
            owner_name=owner.full_name or owner.email,
            vehicle_name=alert.vehicle_name,
            license_plate=alert.license_plate,
            alert_type=alert.type,
            severity=alert.severity,
            message=alert.message,
            detail=alert.detail,
        )
        ok = send_email(owner.email, subject, html)
        if ok:
            logger.debug("Instant alert email sent: owner=%s type=%s vehicle=%s", owner.id, alert.type, alert.vehicle_id)
        else:
            logger.warning("Instant alert email failed: owner=%s type=%s", owner.id, alert.type)
    except Exception as exc:
        logger.error("Error sending instant alert email for owner %s: %s", owner.id, exc)


def process_instant_alert_emails(db: Session) -> None:
    """Detect new/upgraded alerts and send instant emails. Called every 15 minutes."""
    now = datetime.now(timezone.utc)

    for owner in _active_owners(db):
        try:
            alerts = compute_alerts(db, owner.id)
            current_map = {(a.vehicle_id, a.type): a for a in alerts}

            states = (
                db.query(AlertState)
                .filter(AlertState.owner_id == owner.id)
                .all()
            )
            existing_map = {(s.vehicle_id, s.alert_type): s for s in states}

            # Remove stale alert states (alert has resolved)
            for key, state in existing_map.items():
                if key not in current_map:
                    db.delete(state)

            # Process current alerts
            for key, alert in current_map.items():
                if key not in existing_map:
                    # Brand new alert
                    new_state = AlertState(
                        owner_id=owner.id,
                        vehicle_id=alert.vehicle_id,
                        alert_type=alert.type,
                        severity=alert.severity,
                        instant_email_sent=False,
                        first_seen_at=now,
                        last_seen_at=now,
                    )
                    db.add(new_state)
                    db.flush()
                    _send_instant(owner, alert)
                    new_state.instant_email_sent = True
                else:
                    state = existing_map[key]
                    state.last_seen_at = now

                    # Severity upgrade: warning → critical triggers re-notification
                    if state.severity == "warning" and alert.severity == "critical":
                        state.severity = "critical"
                        _send_instant(owner, alert)

            db.commit()

        except Exception as exc:
            logger.error("Instant alert email processing failed for owner %s: %s", owner.id, exc)
            db.rollback()


def send_daily_digest_emails(db: Session) -> None:
    """Send nightly digest of all unresolved alerts. Called at 22:00."""
    for owner in _active_owners(db):
        try:
            alerts = compute_alerts(db, owner.id)
            if not alerts:
                continue

            subject, html = build_daily_digest_email(
                owner_name=owner.full_name or owner.email,
                alerts=alerts,
            )
            ok = send_email(owner.email, subject, html)
            if ok:
                logger.info("Daily digest sent to owner %s — %d alert(s)", owner.id, len(alerts))
            else:
                logger.warning("Daily digest failed for owner %s", owner.id)

        except Exception as exc:
            logger.error("Daily digest error for owner %s: %s", owner.id, exc)
