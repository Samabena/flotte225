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


_EMAIL_BASE = """<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background-color:#f4f6f9;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color:#f4f6f9;padding:40px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="max-width:600px;width:100%;">

          <!-- Header -->
          <tr>
            <td align="center" style="background-color:#1a3c5e;border-radius:12px 12px 0 0;padding:32px 40px;">
              <span style="font-size:28px;font-weight:700;color:#ffffff;letter-spacing:1px;">🚗 Flotte225</span>
              <p style="margin:6px 0 0;color:#93b8d8;font-size:13px;letter-spacing:0.5px;">Gestion intelligente de flotte automobile</p>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="background-color:#ffffff;padding:40px 48px;">
              {content}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td align="center" style="background-color:#f0f4f8;border-radius:0 0 12px 12px;padding:24px 40px;border-top:1px solid #e2e8f0;">
              <p style="margin:0 0 6px;font-size:12px;color:#718096;">
                Cet email a été envoyé automatiquement — merci de ne pas y répondre.
              </p>
              <p style="margin:0;font-size:12px;color:#a0aec0;">
                &copy; {year} Flotte225 · Côte d'Ivoire
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""

_VERIFY_CONTENT = """
<h2 style="margin:0 0 8px;font-size:22px;color:#1a3c5e;">Bienvenue sur Flotte225&nbsp;!</h2>
<p style="margin:0 0 24px;font-size:15px;color:#4a5568;line-height:1.6;">
  Merci de vous être inscrit. Pour activer votre compte, veuillez saisir le code de vérification ci-dessous dans l'application.
</p>

<!-- OTP Box -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
  <tr>
    <td align="center">
      <div style="display:inline-block;background-color:#f0f7ff;border:2px dashed #3b82f6;border-radius:12px;padding:20px 48px;">
        <p style="margin:0 0 4px;font-size:12px;color:#3b82f6;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;">Code de vérification</p>
        <p style="margin:0;font-size:40px;font-weight:800;color:#1a3c5e;letter-spacing:10px;font-family:'Courier New',monospace;">{code}</p>
      </div>
    </td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
  <tr>
    <td style="background-color:#fffbeb;border-left:4px solid #f59e0b;border-radius:4px;padding:12px 16px;">
      <p style="margin:0;font-size:13px;color:#92400e;">
        ⏱ Ce code est valable pendant <strong>15 minutes</strong> uniquement.
      </p>
    </td>
  </tr>
</table>

<p style="margin:0;font-size:13px;color:#a0aec0;line-height:1.6;">
  Si vous n'avez pas créé de compte sur Flotte225, vous pouvez ignorer cet email en toute sécurité.
</p>
"""

_RESET_CONTENT = """
<h2 style="margin:0 0 8px;font-size:22px;color:#1a3c5e;">Réinitialisation de mot de passe</h2>
<p style="margin:0 0 24px;font-size:15px;color:#4a5568;line-height:1.6;">
  Nous avons reçu une demande de réinitialisation du mot de passe associé à votre compte. Utilisez le code ci-dessous pour procéder.
</p>

<!-- OTP Box -->
<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 28px;">
  <tr>
    <td align="center">
      <div style="display:inline-block;background-color:#fff1f2;border:2px dashed #ef4444;border-radius:12px;padding:20px 48px;">
        <p style="margin:0 0 4px;font-size:12px;color:#ef4444;font-weight:600;text-transform:uppercase;letter-spacing:1.5px;">Code de réinitialisation</p>
        <p style="margin:0;font-size:40px;font-weight:800;color:#1a3c5e;letter-spacing:10px;font-family:'Courier New',monospace;">{code}</p>
      </div>
    </td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:24px;">
  <tr>
    <td style="background-color:#fffbeb;border-left:4px solid #f59e0b;border-radius:4px;padding:12px 16px;">
      <p style="margin:0;font-size:13px;color:#92400e;">
        ⏱ Ce code est valable pendant <strong>15 minutes</strong> uniquement.
      </p>
    </td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0">
  <tr>
    <td style="background-color:#fef2f2;border-left:4px solid #ef4444;border-radius:4px;padding:12px 16px;">
      <p style="margin:0;font-size:13px;color:#991b1b;">
        🔒 Si vous n'êtes pas à l'origine de cette demande, ignorez cet email. Votre mot de passe reste inchangé.
      </p>
    </td>
  </tr>
</table>
"""


_ALERT_TYPE_LABELS = {
    "insurance_expiry":    "Assurance",
    "inspection_expiry":   "Contrôle technique",
    "oil_change":          "Vidange",
    "consumption_anomaly": "Consommation anormale",
    "cost_spike":          "Coût carburant élevé",
}

_INSTANT_ALERT_CONTENT = """
<p style="margin:0 0 6px;font-size:15px;color:#4a5568;">Bonjour <strong>{owner_name}</strong>,</p>
<p style="margin:0 0 24px;font-size:15px;color:#4a5568;line-height:1.6;">
  Une nouvelle alerte a été détectée sur votre flotte.
</p>

<div style="border-left:4px solid {severity_color};background:#fafafa;border-radius:8px;padding:16px 20px;margin:0 0 24px;">
  <p style="margin:0 0 8px;font-size:16px;font-weight:700;color:#1a3c5e;">
    {vehicle_name} &nbsp;<span style="font-size:13px;font-weight:400;color:#718096;">({license_plate})</span>
  </p>
  <p style="margin:0 0 10px;">
    <span style="background-color:{severity_color};color:#fff;border-radius:4px;padding:2px 10px;font-size:12px;font-weight:600;">
      {severity_label}
    </span>
    &nbsp;
    <span style="font-size:13px;color:#4a5568;">{alert_type_label}</span>
  </p>
  <p style="margin:0 0 6px;font-size:14px;color:#2d3748;">{message}</p>
  <p style="margin:0;font-size:13px;color:#718096;">{detail}</p>
</div>

<table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
  <tr>
    <td align="center">
      <a href="https://flotte225.ci"
         style="display:inline-block;background-color:#1a3c5e;color:#ffffff;text-decoration:none;
                padding:12px 32px;border-radius:8px;font-size:15px;font-weight:600;">
        Voir le tableau de bord
      </a>
    </td>
  </tr>
</table>

<p style="margin:0;font-size:12px;color:#a0aec0;text-align:center;">
  Désactivez ces notifications dans <strong>Paramètres → Alertes Email</strong>.
</p>
"""

_DIGEST_ROW = (
    '<tr style="background-color:{row_bg};">'
    '<td style="padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;">{vehicle_name}</td>'
    '<td style="padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;color:#718096;">{license_plate}</td>'
    '<td style="padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;">{alert_type_label}</td>'
    '<td style="padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;">'
    '<span style="background-color:{severity_color};color:#fff;border-radius:4px;padding:1px 8px;font-size:11px;font-weight:600;">'
    '{severity_label}</span></td>'
    '<td style="padding:8px 12px;border:1px solid #e2e8f0;font-size:13px;">{message}</td>'
    "</tr>"
)

_DIGEST_CONTENT = """
<p style="margin:0 0 6px;font-size:15px;color:#4a5568;">Bonjour <strong>{owner_name}</strong>,</p>
<h2 style="margin:0 0 20px;font-size:20px;color:#1a3c5e;">
  Récapitulatif quotidien des alertes — {alert_date}
</h2>

<table cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
  <tr>
    <td style="background-color:#fef2f2;border-radius:6px;padding:10px 20px;margin-right:12px;">
      <span style="font-size:22px;font-weight:800;color:#ef4444;">{critical_count}</span>
      <span style="font-size:13px;color:#991b1b;margin-left:4px;">Critique(s)</span>
    </td>
    <td width="12"></td>
    <td style="background-color:#fffbeb;border-radius:6px;padding:10px 20px;">
      <span style="font-size:22px;font-weight:800;color:#f59e0b;">{warning_count}</span>
      <span style="font-size:13px;color:#92400e;margin-left:4px;">Avertissement(s)</span>
    </td>
  </tr>
</table>

<table width="100%" cellpadding="0" cellspacing="0"
       style="border-collapse:collapse;margin:0 0 24px;">
  <thead>
    <tr style="background-color:#f0f4f8;">
      <th style="padding:10px 12px;border:1px solid #e2e8f0;font-size:12px;text-align:left;color:#4a5568;text-transform:uppercase;">Véhicule</th>
      <th style="padding:10px 12px;border:1px solid #e2e8f0;font-size:12px;text-align:left;color:#4a5568;text-transform:uppercase;">Immatriculation</th>
      <th style="padding:10px 12px;border:1px solid #e2e8f0;font-size:12px;text-align:left;color:#4a5568;text-transform:uppercase;">Type</th>
      <th style="padding:10px 12px;border:1px solid #e2e8f0;font-size:12px;text-align:left;color:#4a5568;text-transform:uppercase;">Niveau</th>
      <th style="padding:10px 12px;border:1px solid #e2e8f0;font-size:12px;text-align:left;color:#4a5568;text-transform:uppercase;">Message</th>
    </tr>
  </thead>
  <tbody>
    {alert_rows_html}
  </tbody>
</table>

<p style="margin:0;font-size:12px;color:#a0aec0;text-align:center;">
  Récapitulatif envoyé chaque soir à 22h00. Gérez vos préférences dans
  <strong>Paramètres → Alertes Email</strong>.
</p>
"""


def build_instant_alert_email(
    owner_name: str,
    vehicle_name: str,
    license_plate: str,
    alert_type: str,
    severity: str,
    message: str,
    detail: str,
) -> tuple[str, str]:
    """Returns (subject, html_body) for a single instant alert. Does NOT call send_email."""
    from datetime import date

    severity_label = "Critique" if severity == "critical" else "Avertissement"
    severity_color = "#ef4444" if severity == "critical" else "#f59e0b"
    alert_type_label = _ALERT_TYPE_LABELS.get(alert_type, alert_type)

    subject = f"Flotte225 — Alerte {severity_label} : {vehicle_name}"
    content = _INSTANT_ALERT_CONTENT.format(
        owner_name=owner_name,
        vehicle_name=vehicle_name,
        license_plate=license_plate,
        alert_type_label=alert_type_label,
        severity_label=severity_label,
        severity_color=severity_color,
        message=message,
        detail=detail,
    )
    html = _EMAIL_BASE.format(subject=subject, content=content, year=date.today().year)
    return subject, html


def build_daily_digest_email(
    owner_name: str,
    alerts: list,
) -> tuple[str, str]:
    """Returns (subject, html_body) for the daily alert digest. Does NOT call send_email."""
    from datetime import date

    today = date.today()
    alert_date = today.strftime("%d/%m/%Y")
    subject = f"Flotte225 — Récapitulatif alertes du {alert_date}"

    critical_count = sum(1 for a in alerts if a.severity == "critical")
    warning_count = sum(1 for a in alerts if a.severity == "warning")

    rows_html = ""
    for a in alerts:
        severity_color = "#ef4444" if a.severity == "critical" else "#f59e0b"
        severity_label = "Critique" if a.severity == "critical" else "Avertissement"
        row_bg = "#fef2f2" if a.severity == "critical" else "#fffbeb"
        rows_html += _DIGEST_ROW.format(
            row_bg=row_bg,
            vehicle_name=a.vehicle_name,
            license_plate=a.license_plate,
            alert_type_label=_ALERT_TYPE_LABELS.get(a.type, a.type),
            severity_color=severity_color,
            severity_label=severity_label,
            message=a.message,
        )

    content = _DIGEST_CONTENT.format(
        owner_name=owner_name,
        alert_date=alert_date,
        critical_count=critical_count,
        warning_count=warning_count,
        alert_rows_html=rows_html,
    )
    html = _EMAIL_BASE.format(subject=subject, content=content, year=today.year)
    return subject, html


def send_otp_email(to: str, code: str, purpose: str) -> bool:
    from datetime import date

    year = date.today().year

    if purpose == "EMAIL_VERIFY":
        subject = "Flotte225 — Votre code de vérification"
        content = _VERIFY_CONTENT.format(code=code)
    else:  # PASSWORD_RESET
        subject = "Flotte225 — Réinitialisation de mot de passe"
        content = _RESET_CONTENT.format(code=code)

    body = _EMAIL_BASE.format(subject=subject, content=content, year=year)
    return send_email(to, subject, body)
