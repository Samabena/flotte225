"""
APScheduler setup
  Sprint 9  Instant alert emails (every 15 min) + daily digest at 22:00
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Africa/Abidjan")


def _instant_alert_emails() -> None:
    """Every-15-min job: detect new/upgraded alerts and send instant emails."""
    try:
        from app.core.database import SessionLocal
        from app.services.alert_email_service import process_instant_alert_emails

        db = SessionLocal()
        try:
            process_instant_alert_emails(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Instant alert email job failed: %s", exc)


def _daily_digest_emails() -> None:
    """Daily 22:00 job: send summary digest of all unresolved alerts."""
    try:
        from app.core.database import SessionLocal
        from app.services.alert_email_service import send_daily_digest_emails

        db = SessionLocal()
        try:
            send_daily_digest_emails(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Daily digest email job failed: %s", exc)


def start_scheduler() -> None:
    if scheduler.running:
        return

    # Instant alert emails — check every 15 minutes for new/upgraded alerts
    scheduler.add_job(
        _instant_alert_emails,
        trigger=IntervalTrigger(minutes=15),
        id="instant_alert_emails",
        replace_existing=True,
        max_instances=1,
    )

    # Daily alert digest at 22:00 Africa/Abidjan
    scheduler.add_job(
        _daily_digest_emails,
        trigger=CronTrigger(hour=22, minute=0),
        id="daily_digest_emails",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started — digest@22:00, instant_alerts every 15 min",
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
