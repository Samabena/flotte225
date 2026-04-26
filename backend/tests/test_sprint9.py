"""
Tests for Sprint 9 — Alert Email Notifications
  Instant alert email: edge-detects new/upgraded alerts, sends immediately
  Daily digest email: nightly summary of all unresolved alerts
  First-run backfill: no blast of emails on first deployment
"""
from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch

import pytest

from app.models.alert_state import AlertState
from app.models.maintenance import Maintenance
from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan
from app.models.vehicle import Vehicle
from app.services.alert_email_service import (
    process_instant_alert_emails,
    send_daily_digest_emails,
)
from app.services.email_service import (
    build_daily_digest_email,
    build_instant_alert_email,
)


# ── Helpers ───────────────────────────────────────────────────────────────────


def _seed_plans(db):
    from scripts.seed import PLANS

    for plan_data in PLANS:
        if (
            not db.query(SubscriptionPlan)
            .filter(SubscriptionPlan.name == plan_data["name"])
            .first()
        ):
            db.add(SubscriptionPlan(**plan_data))
    db.commit()


def _register_and_verify(client, db, email):
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post(
            "/api/v1/auth/register",
            json={"full_name": "Alert Tester", "email": email, "password": "Password1"},
        )
    otp = (
        db.query(OtpCode)
        .filter(OtpCode.purpose == "EMAIL_VERIFY")
        .order_by(OtpCode.id.desc())
        .first()
    )
    client.post("/api/v1/auth/verify-email", json={"email": email, "code": otp.code})
    res = client.post("/api/v1/auth/login", json={"identifier": email, "password": "Password1"})
    return res.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _owner_id(token):
    from app.core.security import decode_access_token
    return int(decode_access_token(token)["sub"])


def _create_vehicle(client, headers, plate):
    res = client.post(
        "/api/v1/vehicles",
        json={
            "name": "Véhicule Test",
            "brand": "Toyota",
            "model": "HiLux",
            "license_plate": plate,
            "fuel_type": "Diesel",
            "initial_mileage": 10000,
        },
        headers=headers,
    )
    assert res.status_code in (200, 201), res.text
    return res.json()["data"]["id"]


def _set_insurance_expiry(client, headers, vehicle_id, expiry_date: date):
    client.put(
        f"/api/v1/vehicles/{vehicle_id}/maintenance",
        json={"insurance_expiry": str(expiry_date)},
        headers=headers,
    )


# ── Email builder unit tests ──────────────────────────────────────────────────


class TestBuildInstantAlertEmail:
    def test_subject_contains_critique_for_critical(self):
        subject, html = build_instant_alert_email(
            owner_name="Jean Dupont",
            vehicle_name="Toyota HiLux",
            license_plate="CI-001-AB",
            alert_type="insurance_expiry",
            severity="critical",
            message="Assurance expirée",
            detail="Expirée depuis 5 jours.",
        )
        assert "Critique" in subject
        assert "Toyota HiLux" in subject

    def test_subject_contains_avertissement_for_warning(self):
        subject, html = build_instant_alert_email(
            owner_name="Jean Dupont",
            vehicle_name="Pickup",
            license_plate="CI-002-AB",
            alert_type="oil_change",
            severity="warning",
            message="Vidange proche",
            detail="450 km depuis la dernière vidange.",
        )
        assert "Avertissement" in subject

    def test_html_contains_vehicle_details(self):
        _, html = build_instant_alert_email(
            owner_name="Marie",
            vehicle_name="Renault Kangoo",
            license_plate="AB-123-CI",
            alert_type="oil_change",
            severity="warning",
            message="Vidange proche",
            detail="400 km depuis la dernière vidange.",
        )
        assert "Renault Kangoo" in html
        assert "AB-123-CI" in html
        assert "400 km" in html

    def test_unknown_alert_type_does_not_crash(self):
        subject, html = build_instant_alert_email(
            owner_name="Test",
            vehicle_name="Véhicule",
            license_plate="XX-000-CI",
            alert_type="unknown_future_type",
            severity="warning",
            message="Alerte inconnue",
            detail="",
        )
        assert subject
        assert html


class TestBuildDailyDigestEmail:
    def _make_alert(self, severity="critical"):
        from app.schemas.alert import AlertResponse
        return AlertResponse(
            vehicle_id=1,
            vehicle_name="Toyota",
            license_plate="CI-100-AB",
            type="insurance_expiry",
            severity=severity,
            message="Assurance expirée",
            detail="Expirée depuis 3 jours.",
        )

    def test_subject_contains_today_date(self):
        subject, _ = build_daily_digest_email("Owner", [self._make_alert()])
        assert date.today().strftime("%d/%m/%Y") in subject

    def test_html_contains_alert_counts(self):
        from app.schemas.alert import AlertResponse
        alerts = [
            self._make_alert("critical"),
            self._make_alert("critical"),
            self._make_alert("warning"),
        ]
        _, html = build_daily_digest_email("Owner", alerts)
        assert ">2<" in html or "2 " in html
        assert ">1<" in html or "1 " in html

    def test_empty_alert_list_returns_valid_html(self):
        subject, html = build_daily_digest_email("Owner", [])
        assert subject
        assert "<!DOCTYPE html>" in html


# ── Reconciliation service tests ──────────────────────────────────────────────


class TestProcessInstantAlertEmails:
    """Uses real DB (in-memory test transaction) + mocked send_email."""

    def _setup_owner_with_critical_alert(self, client, db):
        """Register owner, create vehicle, set expired insurance (→ critical alert)."""
        _seed_plans(db)
        token = _register_and_verify(client, db, "alert.instant@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-001-CI")
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=5))
        return oid, vid

    def test_new_alert_creates_state_and_sends_email(self, client, db):
        oid, vid = self._setup_owner_with_critical_alert(client, db)

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            process_instant_alert_emails(db)

        # AlertState row should exist
        state = (
            db.query(AlertState)
            .filter(AlertState.owner_id == oid, AlertState.alert_type == "insurance_expiry")
            .first()
        )
        assert state is not None
        assert state.severity == "critical"
        assert state.instant_email_sent is True
        # Email sent exactly once
        mock_send.assert_called_once()

    def test_second_run_does_not_resend(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "alert.norepeat@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-002-CI")
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=5))

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            # First run: backfill (first-run protection → no email)
            process_instant_alert_emails(db)
            first_call_count = mock_send.call_count
            # Second run: alert already in state → no new email
            process_instant_alert_emails(db)
            assert mock_send.call_count == first_call_count  # unchanged

    def test_first_detection_sends_email_and_records_state(self, client, db):
        """Every new alert triggers an email on its very first detection."""
        _seed_plans(db)
        token = _register_and_verify(client, db, "alert.firstdetect@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-003-CI")
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=10))

        count_before = db.query(AlertState).filter(AlertState.owner_id == oid).count()
        assert count_before == 0

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            process_instant_alert_emails(db)

        mock_send.assert_called_once()
        state = db.query(AlertState).filter(AlertState.owner_id == oid).first()
        assert state is not None
        assert state.instant_email_sent is True

    def test_resolved_alert_deletes_state_row(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "alert.resolve@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-004-CI")

        # Manually insert a stale AlertState for a vehicle with no active alert
        stale_state = AlertState(
            owner_id=oid,
            vehicle_id=vid,
            alert_type="insurance_expiry",
            severity="critical",
            instant_email_sent=True,
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(stale_state)
        db.commit()

        # No insurance_expiry set → compute_alerts returns nothing for this vehicle
        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            process_instant_alert_emails(db)

        stale_check = db.query(AlertState).filter(AlertState.owner_id == oid).first()
        assert stale_check is None
        mock_send.assert_not_called()

    def test_severity_upgrade_triggers_resend(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "alert.upgrade@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-005-CI")

        # Set insurance to 10 days ahead → warning
        _set_insurance_expiry(client, _headers(token), vid, date.today() + timedelta(days=10))

        # Manually pre-insert a warning state (simulate a previous cycle)
        warn_state = AlertState(
            owner_id=oid,
            vehicle_id=vid,
            alert_type="insurance_expiry",
            severity="warning",
            instant_email_sent=True,  # already sent for warning
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc),
        )
        db.add(warn_state)
        db.commit()

        # Now expire the insurance → critical
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=1))

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            process_instant_alert_emails(db)

        # Email should be sent for the upgrade
        mock_send.assert_called_once()

        # State row should reflect new severity
        state = db.query(AlertState).filter(AlertState.owner_id == oid).first()
        assert state.severity == "critical"

    def test_email_alerts_disabled_owner_skipped(self, client, db):
        from app.models.user import User

        _seed_plans(db)
        token = _register_and_verify(client, db, "alert.disabled@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-006-CI")
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=5))

        # Disable email alerts
        owner = db.query(User).filter(User.id == oid).first()
        owner.email_alerts_enabled = False
        db.commit()

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            process_instant_alert_emails(db)

        mock_send.assert_not_called()
        # No state rows created either
        count = db.query(AlertState).filter(AlertState.owner_id == oid).count()
        assert count == 0


# ── Daily digest tests ────────────────────────────────────────────────────────


class TestSendDailyDigestEmails:
    def test_digest_skips_owner_with_no_alerts(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "digest.empty@test.ci")
        # No vehicle → no alerts

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            send_daily_digest_emails(db)

        mock_send.assert_not_called()

    def test_digest_sends_when_alerts_exist(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "digest.active@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-DG1-CI")
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=3))

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            send_daily_digest_emails(db)

        mock_send.assert_called_once()
        # Verify the subject contains the date
        call_args = mock_send.call_args
        subject = call_args[0][1]
        assert date.today().strftime("%d/%m/%Y") in subject

    def test_digest_skips_owner_with_alerts_disabled(self, client, db):
        from app.models.user import User

        _seed_plans(db)
        token = _register_and_verify(client, db, "digest.disabled@test.ci")
        oid = _owner_id(token)
        vid = _create_vehicle(client, _headers(token), "SP9-DG2-CI")
        _set_insurance_expiry(client, _headers(token), vid, date.today() - timedelta(days=3))

        owner = db.query(User).filter(User.id == oid).first()
        owner.email_alerts_enabled = False
        db.commit()

        with patch("app.services.alert_email_service.send_email", return_value=True) as mock_send:
            send_daily_digest_emails(db)

        mock_send.assert_not_called()
