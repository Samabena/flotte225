"""
WhatsApp notification service — Sprint 7
  US-035  Send critical fleet alerts via WhatsApp (Meta Cloud API)

Non-blocking: silently skips if env vars or owner number are missing.
"""
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

_MAX_ALERTS_PER_MESSAGE = 5


def send_whatsapp_message(to: str, message: str) -> bool:
    """
    Send a free-text WhatsApp message via Meta Cloud API.
    Returns True on success, False on any failure.
    """
    if not settings.WHATSAPP_API_URL or not settings.WHATSAPP_TOKEN:
        logger.warning("WhatsApp not configured — message not sent to %s", to)
        return False

    # Normalize: strip spaces, dashes, leading +
    phone = to.replace(" ", "").replace("-", "").lstrip("+")

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": message},
    }

    try:
        response = httpx.post(
            settings.WHATSAPP_API_URL,
            headers={
                "Authorization": f"Bearer {settings.WHATSAPP_TOKEN}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=10.0,
        )
        if response.status_code >= 400:
            logger.error(
                "WhatsApp API error %s for %s: %s",
                response.status_code, to, response.text,
            )
            return False
        return True
    except Exception as exc:
        logger.error("WhatsApp exception for %s: %s", to, exc)
        return False


def send_fleet_alerts_to_owner(
    owner_whatsapp: str,
    owner_name: str,
    alerts: list,
) -> bool:
    """
    Filter critical alerts and send a summary WhatsApp message to the owner.
    Skips silently if no critical alerts or no valid number.
    """
    if not owner_whatsapp:
        return False

    critical = [a for a in alerts if a.severity == "critical"]
    if not critical:
        return True

    lines = [f"🚨 Flotte225 — Alertes critiques pour {owner_name} :"]
    for a in critical[:_MAX_ALERTS_PER_MESSAGE]:
        lines.append(f"• {a.vehicle_name} : {a.message}")
    if len(critical) > _MAX_ALERTS_PER_MESSAGE:
        lines.append(f"… et {len(critical) - _MAX_ALERTS_PER_MESSAGE} alerte(s) supplémentaire(s).")
    lines.append("\nConnectez-vous sur Flotte225 pour voir le détail.")

    return send_whatsapp_message(owner_whatsapp, "\n".join(lines))
