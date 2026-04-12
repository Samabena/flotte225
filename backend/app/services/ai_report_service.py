"""
AI Report Service — Sprint 8
  US-032  On-demand AI fleet report (Pro/Business, ≤5/month on Pro)
  US-033  Scheduled AI reports (weekly / monthly, Business only)

Flow: build fleet snapshot → structured French prompt → OpenRouter LLM → email via SendGrid.
Non-blocking on email failure; raises on plan/quota violations.
"""
import logging
from datetime import date, datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.fuel_entry import FuelEntry
from app.models.maintenance import Maintenance
from app.models.report_schedule import ReportSchedule
from app.models.subscription import OwnerSubscription, SubscriptionPlan
from app.models.vehicle import Vehicle
from app.services.alert_service import compute_alerts
from app.services.email_service import send_email

logger = logging.getLogger(__name__)

_PRO_MONTHLY_LIMIT = 5
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT = 90.0


# ── Public API ────────────────────────────────────────────────────────────────

def generate_report_on_demand(db: Session, owner_id: int, owner_email: str, owner_name: str) -> dict:
    """
    Generate a report immediately for the given owner.
    Checks plan quota, calls LLM, emails result.
    Returns {"status": "sent", "used": N, "limit": N|None}.
    Raises ValueError on quota/plan violation.
    """
    plan, sub = _get_plan_and_sub(db, owner_id)
    _assert_ai_reports_allowed(plan)

    schedule = _get_or_create_schedule(db, owner_id)
    _maybe_reset_monthly_counter(db, schedule)

    limit = plan.ai_reports_per_month  # None = unlimited (Business)
    if limit is not None and schedule.ai_reports_used_month >= limit:
        raise ValueError(
            f"Limite mensuelle atteinte ({limit} rapport(s) par mois sur le plan Pro). "
            "Passez au plan Business pour des rapports illimités."
        )

    report_text = _call_openrouter(db, owner_id, owner_name)
    _send_report_email(owner_email, owner_name, report_text)

    schedule.ai_reports_used_month += 1
    schedule.last_sent_at = datetime.now(timezone.utc)
    schedule.last_status = "sent"
    db.commit()

    return {
        "status": "sent",
        "used": schedule.ai_reports_used_month,
        "limit": limit,
    }


def get_schedule(db: Session, owner_id: int) -> ReportSchedule:
    """Return (or create) the owner's report schedule record."""
    return _get_or_create_schedule(db, owner_id)


def update_schedule(db: Session, owner_id: int, enabled: bool, frequency: str | None) -> ReportSchedule:
    """Enable/disable scheduled reports and set frequency."""
    if enabled and frequency not in ("weekly", "monthly"):
        raise ValueError("La fréquence doit être 'weekly' ou 'monthly' pour activer les rapports planifiés.")

    plan, _ = _get_plan_and_sub(db, owner_id)
    if enabled:
        _assert_scheduled_reports_allowed(plan)

    schedule = _get_or_create_schedule(db, owner_id)
    schedule.enabled = enabled
    schedule.frequency = frequency if enabled else schedule.frequency
    schedule.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(schedule)
    return schedule


def run_scheduled_reports(db: Session) -> None:
    """
    Called by APScheduler. For every owner with an enabled schedule whose
    cadence has elapsed, generate and email a report.
    """
    from app.models.user import User

    now = datetime.now(timezone.utc)
    schedules = db.query(ReportSchedule).filter(ReportSchedule.enabled == True).all()

    for sched in schedules:
        if not _cadence_elapsed(sched, now):
            continue
        owner = db.get(User, sched.owner_id)
        if not owner or not owner.is_active:
            continue
        try:
            plan, _ = _get_plan_and_sub(db, sched.owner_id)
            _assert_scheduled_reports_allowed(plan)
            _maybe_reset_monthly_counter(db, sched)

            report_text = _call_openrouter(db, sched.owner_id, owner.full_name)
            _send_report_email(owner.email, owner.full_name, report_text)

            sched.last_sent_at = now
            sched.last_status = "sent"
            sched.ai_reports_used_month += 1
            db.commit()
        except Exception as exc:
            logger.error("Scheduled AI report failed for owner %s: %s", sched.owner_id, exc)
            sched.last_status = "failed"
            db.commit()


# ── Internal helpers ──────────────────────────────────────────────────────────

def _get_plan_and_sub(db: Session, owner_id: int):
    sub = (
        db.query(OwnerSubscription)
        .filter(OwnerSubscription.owner_id == owner_id, OwnerSubscription.is_active == True)
        .first()
    )
    if not sub:
        raise ValueError("Aucun abonnement actif.")
    plan = db.get(SubscriptionPlan, sub.plan_id)
    if not plan:
        raise ValueError("Plan introuvable.")
    return plan, sub


def _assert_ai_reports_allowed(plan: SubscriptionPlan) -> None:
    if plan.name == "starter":
        raise ValueError("Les rapports IA ne sont pas disponibles sur le plan Starter.")


def _assert_scheduled_reports_allowed(plan: SubscriptionPlan) -> None:
    if plan.name != "business":
        raise ValueError("Les rapports planifiés nécessitent un abonnement Business.")


def _get_or_create_schedule(db: Session, owner_id: int) -> ReportSchedule:
    sched = db.query(ReportSchedule).filter(ReportSchedule.owner_id == owner_id).first()
    if not sched:
        sched = ReportSchedule(owner_id=owner_id)
        db.add(sched)
        db.commit()
        db.refresh(sched)
    return sched


def _maybe_reset_monthly_counter(db: Session, schedule: ReportSchedule) -> None:
    today = date.today()
    if schedule.usage_reset_at is None or schedule.usage_reset_at.month != today.month:
        schedule.ai_reports_used_month = 0
        schedule.usage_reset_at = today
        db.commit()


def _cadence_elapsed(sched: ReportSchedule, now: datetime) -> bool:
    if sched.last_sent_at is None:
        return True
    delta = now - sched.last_sent_at
    if sched.frequency == "weekly":
        return delta.days >= 7
    if sched.frequency == "monthly":
        return delta.days >= 28
    return False


def _build_fleet_snapshot(db: Session, owner_id: int) -> dict:
    """Collect fleet data into a JSON-serialisable dict for the LLM prompt."""
    vehicles = db.query(Vehicle).filter(
        Vehicle.owner_id == owner_id,
        Vehicle.status != "archived",
    ).all()

    vehicle_data = []
    for v in vehicles:
        entries = (
            db.query(FuelEntry)
            .filter(FuelEntry.vehicle_id == v.id)
            .order_by(FuelEntry.date.desc())
            .limit(10)
            .all()
        )
        maintenance = db.query(Maintenance).filter(Maintenance.vehicle_id == v.id).first()
        vehicle_data.append({
            "name": v.name,
            "brand": v.brand,
            "model": v.model,
            "status": v.status,
            "fuel_entries": [
                {
                    "date": str(e.date),
                    "liters": float(e.liters),
                    "amount_fcfa": float(e.amount_fcfa),
                    "consumption_per_100km": float(e.consumption_per_100km) if e.consumption_per_100km else None,
                }
                for e in entries
            ],
            "maintenance": {
                "last_oil_change_km": maintenance.last_oil_change_km if maintenance else None,
                "insurance_expiry": str(maintenance.insurance_expiry) if maintenance and maintenance.insurance_expiry else None,
                "inspection_expiry": str(maintenance.inspection_expiry) if maintenance and maintenance.inspection_expiry else None,
            } if maintenance else None,
        })

    alerts = compute_alerts(db, owner_id)
    alert_summary = [
        {"vehicle": a.vehicle_name, "severity": a.severity, "message": a.message}
        for a in alerts
    ]

    return {
        "total_vehicles": len(vehicles),
        "vehicles": vehicle_data,
        "alerts": alert_summary,
        "generated_at": datetime.now(timezone.utc).strftime("%d/%m/%Y"),
    }


def _call_openrouter(db: Session, owner_id: int, owner_name: str) -> str:
    """Call OpenRouter and return the generated French report text."""
    if not settings.OPENROUTER_API_KEY:
        logger.warning("OPENROUTER_API_KEY not set — returning placeholder report")
        return "[Rapport IA non disponible : clé API manquante]"

    snapshot = _build_fleet_snapshot(db, owner_id)

    system_prompt = (
        "Tu es un assistant spécialisé en gestion de flotte automobile en Côte d'Ivoire. "
        "Tu analyses les données de flotte et produis des rapports clairs, concis et professionnels "
        "en français. Ton rapport doit être lisible par un propriétaire non-technique. "
        "Utilise des sections avec des titres courts, des points clés, et des recommandations concrètes."
    )

    user_prompt = (
        f"Génère un rapport de performance de flotte pour {owner_name}.\n\n"
        f"Données de flotte :\n{snapshot}\n\n"
        "Le rapport doit inclure :\n"
        "1. Résumé exécutif (2-3 phrases)\n"
        "2. État de la flotte (véhicules actifs, alertes importantes)\n"
        "3. Consommation de carburant (tendances, véhicules à surveiller)\n"
        "4. Maintenance (échéances proches ou dépassées)\n"
        "5. Recommandations (3 actions prioritaires)\n\n"
        "Sois direct et pratique. Évite le jargon technique."
    )

    try:
        response = httpx.post(
            _OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {settings.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://flotte225.ci",
                "X-Title": "Flotte225",
            },
            json={
                "model": settings.OPENROUTER_MODEL,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": 1500,
                "temperature": 0.4,
            },
            timeout=_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data["choices"][0]["message"]["content"]
    except httpx.TimeoutException:
        logger.error("OpenRouter timeout for owner %s", owner_id)
        raise ValueError("Le service IA n'a pas répondu dans les délais. Réessayez dans quelques minutes.")
    except Exception as exc:
        logger.error("OpenRouter error for owner %s: %s", owner_id, exc)
        raise ValueError("Erreur lors de la génération du rapport IA. Réessayez plus tard.")


def _send_report_email(to: str, owner_name: str, report_text: str) -> None:
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 700px; margin: auto;">
      <h2 style="color: #005F02;">Rapport de flotte Flotte225</h2>
      <p>Bonjour <strong>{owner_name}</strong>,</p>
      <p>Voici votre rapport de performance de flotte :</p>
      <hr>
      <div style="white-space: pre-wrap; line-height: 1.6;">{report_text}</div>
      <hr>
      <p style="color: #888; font-size: 12px;">
        Rapport généré par Flotte225 — <a href="https://flotte225.ci">flotte225.ci</a>
      </p>
    </div>
    """
    ok = send_email(to, "Votre rapport de flotte Flotte225", html)
    if not ok:
        logger.warning("Failed to email AI report to %s — report was generated but not delivered", to)
