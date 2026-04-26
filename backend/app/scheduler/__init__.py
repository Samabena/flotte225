"""
APScheduler setup — Sprint 7 + Sprint 8 + Sprint 9
  US-035  Daily WhatsApp alert dispatch
  US-029  Periodic webhook dispatch (every WEBHOOK_INTERVAL_HOURS)
  US-033  Scheduled AI reports (weekly / monthly per owner config)
  Sprint 9  Instant alert emails (every 15 min) + daily digest at 22:00
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="Africa/Abidjan")


def _daily_whatsapp_alerts() -> None:
    """Daily job: send critical fleet alerts via WhatsApp to owners with a number set."""
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
                    User.is_active.is_(True),
                    User.whatsapp_number.isnot(None),
                    User.whatsapp_number != "",
                )
                .all()
            )
            for owner in owners:
                alerts = compute_alerts(db, owner.id)
                send_fleet_alerts_to_owner(
                    owner.whatsapp_number, owner.full_name, alerts
                )
        finally:
            db.close()
    except Exception as exc:
        logger.error("Daily WhatsApp alert job failed: %s", exc)


def _webhook_dispatch() -> None:
    """Periodic job: dispatch fleet summary webhook for all active owners."""
    try:
        from app.core.database import SessionLocal
        from app.services.webhook_service import run_webhook_dispatch

        db = SessionLocal()
        try:
            run_webhook_dispatch(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Webhook dispatch job failed: %s", exc)


def _scheduled_ai_reports() -> None:
    """Hourly job: generate and email AI reports for owners whose cadence has elapsed."""
    try:
        from app.core.database import SessionLocal
        from app.services.ai_report_service import run_scheduled_reports

        db = SessionLocal()
        try:
            run_scheduled_reports(db)
        finally:
            db.close()
    except Exception as exc:
        logger.error("Scheduled AI reports job failed: %s", exc)


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

    # Daily WhatsApp alerts at 08:00 Africa/Abidjan
    scheduler.add_job(
        _daily_whatsapp_alerts,
        trigger=CronTrigger(hour=8, minute=0),
        id="daily_whatsapp_alerts",
        replace_existing=True,
    )

    # Webhook dispatch every N hours (default 24)
    scheduler.add_job(
        _webhook_dispatch,
        trigger=IntervalTrigger(hours=settings.WEBHOOK_INTERVAL_HOURS),
        id="webhook_dispatch",
        replace_existing=True,
    )

    # Scheduled AI reports — checked hourly, each owner's cadence enforced in the service
    scheduler.add_job(
        _scheduled_ai_reports,
        trigger=CronTrigger(minute=30),  # :30 past every hour
        id="scheduled_ai_reports",
        replace_existing=True,
    )

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
        "Scheduler started — WhatsApp@08:00, digest@22:00, instant_alerts every 15 min, "
        "webhook every %sh, AI reports@:30",
        settings.WEBHOOK_INTERVAL_HOURS,
    )


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
