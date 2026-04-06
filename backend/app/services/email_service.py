import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from app.core.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, html_content: str) -> bool:
    """Send an email via SendGrid. Returns True on success, False on failure (non-blocking)."""
    if not settings.SENDGRID_API_KEY:
        logger.warning("SENDGRID_API_KEY not set — email not sent to %s", to)
        return False

    message = Mail(
        from_email=settings.SENDGRID_FROM_EMAIL,
        to_emails=to,
        subject=subject,
        html_content=html_content,
    )
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code >= 400:
            logger.error("SendGrid error %s for %s", response.status_code, to)
            return False
        return True
    except Exception as exc:
        logger.error("SendGrid exception for %s: %s", to, exc)
        return False


def send_otp_email(to: str, code: str, purpose: str) -> bool:
    if purpose == "EMAIL_VERIFY":
        subject = "Flotte225 — Votre code de vérification"
        body = f"""
        <p>Bienvenue sur Flotte225 !</p>
        <p>Votre code de vérification est : <strong style="font-size:24px">{code}</strong></p>
        <p>Ce code expire dans <strong>15 minutes</strong>.</p>
        <p>Si vous n'avez pas créé de compte, ignorez cet email.</p>
        """
    else:  # PASSWORD_RESET
        subject = "Flotte225 — Réinitialisation de mot de passe"
        body = f"""
        <p>Vous avez demandé une réinitialisation de mot de passe.</p>
        <p>Votre code est : <strong style="font-size:24px">{code}</strong></p>
        <p>Ce code expire dans <strong>15 minutes</strong>.</p>
        <p>Si vous n'avez pas fait cette demande, ignorez cet email.</p>
        """
    return send_email(to, subject, body)
