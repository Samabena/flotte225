"""
APScheduler setup — Sprint 7
  US-035  Daily WhatsApp alert dispatch for owners with critical fleet alerts
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Africa/Abidjan")


def _daily_whatsapp_alerts() -> None:
    """
    Daily job: for every active owner with a WhatsApp number, run the alert
    engine and send a summary if any critical alerts are found.
    """
    try:
        from app.core.database import SessionLocal
        from app.models.user import User
        from app.services.alert_service import compute_alerts
        from app.services.whatsapp_service import send_fleet_alerts_to_owner

        db = SessionLocal()
        try:
            owners = (
                db.query(User)
                .filter(
                    User.role == "OWNER",
                    User.is_active == True,
                    User.whatsapp_number.isnot(None),
                    User.whatsapp_number != "",
                )
                .all()
            )
            for owner in owners:
                alerts = compute_alerts(db, owner.id)
                send_fleet_alerts_to_owner(owner.whatsapp_number, owner.full_name, alerts)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Daily WhatsApp alert job failed: %s", exc)


def start_scheduler() -> None:
    if scheduler.running:
        return
    scheduler.add_job(
        _daily_whatsapp_alerts,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_whatsapp_alerts",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — daily WhatsApp alerts at 08:00 Africa/Abidjan")


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
