"""
Quick manual test: send both alert email types to a given address.
Run from the backend container:
  docker compose exec backend python scripts/test_alert_email.py info@abenasamuel.com
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.email_service import (
    build_instant_alert_email,
    build_daily_digest_email,
    send_email,
)
from app.schemas.alert import AlertResponse

TO = sys.argv[1] if len(sys.argv) > 1 else "info@abenasamuel.com"


def test_instant():
    subject, html = build_instant_alert_email(
        owner_name="Samuel",
        vehicle_name="Toyota HiLux",
        license_plate="CI-001-AB",
        alert_type="insurance_expiry",
        severity="critical",
        message="Assurance expirée",
        detail="L'assurance de ce véhicule a expiré il y a 5 jours.",
    )
    ok = send_email(TO, subject, html)
    print(f"[instant / critical]  sent={ok}  subject={subject!r}")

    subject2, html2 = build_instant_alert_email(
        owner_name="Samuel",
        vehicle_name="Renault Kangoo",
        license_plate="CI-099-AB",
        alert_type="oil_change",
        severity="warning",
        message="Vidange recommandée",
        detail="450 km depuis la dernière vidange. Seuil recommandé : 500 km.",
    )
    ok2 = send_email(TO, subject2, html2)
    print(f"[instant / warning ]  sent={ok2}  subject={subject2!r}")


def test_digest():
    alerts = [
        AlertResponse(
            vehicle_id=1,
            vehicle_name="Toyota HiLux",
            license_plate="CI-001-AB",
            type="insurance_expiry",
            severity="critical",
            message="Assurance expirée",
            detail="Expirée depuis 5 jours.",
        ),
        AlertResponse(
            vehicle_id=2,
            vehicle_name="Renault Kangoo",
            license_plate="CI-099-AB",
            type="oil_change",
            severity="warning",
            message="Vidange recommandée",
            detail="450 km depuis la dernière vidange.",
        ),
        AlertResponse(
            vehicle_id=3,
            vehicle_name="Pickup Ford",
            license_plate="CI-222-AB",
            type="inspection_expiry",
            severity="warning",
            message="Contrôle technique bientôt expiré",
            detail="Expire dans 8 jours.",
        ),
    ]
    subject, html = build_daily_digest_email("Samuel", alerts)
    ok = send_email(TO, subject, html)
    print(f"[digest  / 3 alerts]  sent={ok}  subject={subject!r}")


if __name__ == "__main__":
    print(f"Sending test alert emails to: {TO}\n")
    test_instant()
    test_digest()
    print("\nDone.")
