"""
Tests for Sprint 8 — AI Reports & Webhook Integration
  US-029  Automated webhook dispatch
  US-030  View last webhook status
  US-032  Generate on-demand AI fleet report
  US-033  Configure scheduled AI reports
"""

from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

import pytest

from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan, OwnerSubscription


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
            json={
                "full_name": "Test User",
                "email": email,
                "password": "Password1",
            },
        )
    otp = (
        db.query(OtpCode)
        .filter(OtpCode.purpose == "EMAIL_VERIFY")
        .order_by(OtpCode.id.desc())
        .first()
    )
    client.post("/api/v1/auth/verify-email", json={"email": email, "code": otp.code})
    res = client.post(
        "/api/v1/auth/login", json={"identifier": email, "password": "Password1"}
    )
    return res.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_driver_in_db(db, owner_id, username):
    from app.models.user import User
    from app.core.security import hash_password

    driver = User(
        full_name="Test Driver",
        username=username,
        email=None,
        password_hash=hash_password("Password1"),
        role="DRIVER",
        owner_id=owner_id,
        is_verified=True,
        is_active=True,
        is_disabled=False,
    )
    db.add(driver)
    db.commit()
    db.refresh(driver)
    return driver


def _make_driver_token(client, db, owner_token, username):
    owner_id = _get_user_id(owner_token)
    driver = _create_driver_in_db(db, owner_id, username)
    res = client.post(
        "/api/v1/auth/login", json={"identifier": username, "password": "Password1"}
    )
    return res.json()["access_token"], driver.id


def _get_user_id(token):
    from app.core.security import decode_access_token

    return int(decode_access_token(token)["sub"])


def _upgrade_to_plan(db, owner_id, plan_name):
    sub = (
        db.query(OwnerSubscription)
        .filter(OwnerSubscription.owner_id == owner_id)
        .first()
    )
    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()
    sub.plan_id = plan.id
    db.commit()


# ── US-032: On-demand AI report ───────────────────────────────────────────────


class TestReportGenerate:
    @pytest.mark.skip(reason="Subscription tiering deferred — plan gating disabled")
    def test_starter_cannot_generate_report(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep32a@test.ci")
        res = client.post("/api/v1/reports/generate", headers=_headers(token))
        assert res.status_code == 403
        assert "Starter" in res.json()["detail"]

    @pytest.mark.skip(reason="Subscription tiering deferred — plan gating disabled")
    def test_pro_owner_generates_report(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep32b@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "pro")

        with patch(
            "app.services.ai_report_service._call_openrouter",
            return_value="Rapport test.",
        ), patch("app.services.ai_report_service._send_report_email"):
            res = client.post("/api/v1/reports/generate", headers=_headers(token))

        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "sent"
        assert data["used"] == 1
        assert data["limit"] == 5

    @pytest.mark.skip(reason="Subscription tiering deferred — plan gating disabled")
    def test_pro_quota_enforced(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep32c@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "pro")

        # Exhaust quota directly via DB — set usage_reset_at to today so counter is not reset
        from datetime import date
        from app.models.report_schedule import ReportSchedule

        sched = ReportSchedule(
            owner_id=owner_id, ai_reports_used_month=5, usage_reset_at=date.today()
        )
        db.add(sched)
        db.commit()

        res = client.post("/api/v1/reports/generate", headers=_headers(token))
        assert res.status_code == 403
        assert "Limite mensuelle" in res.json()["detail"]

    def test_business_owner_generates_report_no_limit(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep32d@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "business")

        with patch(
            "app.services.ai_report_service._call_openrouter",
            return_value="Rapport business.",
        ), patch("app.services.ai_report_service._send_report_email"):
            res = client.post("/api/v1/reports/generate", headers=_headers(token))

        assert res.status_code == 200
        data = res.json()
        assert data["limit"] is None  # unlimited on Business

    def test_driver_cannot_generate_report(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner32e_helper@test.ci")
        token, _ = _make_driver_token(client, db, owner_token, "rep32e")
        res = client.post("/api/v1/reports/generate", headers=_headers(token))
        assert res.status_code == 403

    def test_unauthenticated_cannot_generate_report(self, client, db):
        res = client.post("/api/v1/reports/generate")
        assert res.status_code == 403


# ── US-033: Schedule configuration ───────────────────────────────────────────


class TestReportSchedule:
    def test_get_schedule_returns_defaults(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33a@test.ci")
        res = client.get("/api/v1/reports/schedule", headers=_headers(token))
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is False
        assert data["ai_reports_used_month"] == 0

    def test_business_owner_can_enable_weekly_schedule(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33b@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "business")

        res = client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": True, "frequency": "weekly"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["enabled"] is True
        assert data["frequency"] == "weekly"

    def test_business_owner_can_enable_monthly_schedule(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33c@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "business")

        res = client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": True, "frequency": "monthly"},
        )
        assert res.status_code == 200
        assert res.json()["frequency"] == "monthly"

    @pytest.mark.skip(reason="Subscription tiering deferred — plan gating disabled")
    def test_pro_owner_cannot_enable_schedule(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33d@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "pro")

        res = client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": True, "frequency": "weekly"},
        )
        assert res.status_code == 403

    @pytest.mark.skip(reason="Subscription tiering deferred — plan gating disabled")
    def test_starter_cannot_enable_schedule(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33e@test.ci")

        res = client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": True, "frequency": "weekly"},
        )
        assert res.status_code == 403

    def test_enable_without_frequency_returns_403(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33f@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "business")

        res = client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": True, "frequency": None},
        )
        assert res.status_code == 403

    def test_disable_schedule(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "rep33g@test.ci")
        owner_id = _get_user_id(token)
        _upgrade_to_plan(db, owner_id, "business")

        # Enable first
        client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": True, "frequency": "monthly"},
        )
        # Disable
        res = client.put(
            "/api/v1/reports/schedule",
            headers=_headers(token),
            json={"enabled": False, "frequency": None},
        )
        assert res.status_code == 200
        assert res.json()["enabled"] is False


# ── US-030: Webhook status ────────────────────────────────────────────────────


class TestWebhookStatus:
    def test_get_status_no_previous_dispatch(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "web30a@test.ci")
        res = client.get("/api/v1/webhook/status", headers=_headers(token))
        assert res.status_code == 200
        data = res.json()
        assert "configured" in data
        assert data["last_sent_at"] is None
        assert data["last_status_code"] is None

    def test_unauthenticated_cannot_view_status(self, client, db):
        res = client.get("/api/v1/webhook/status")
        assert res.status_code == 403

    def test_driver_cannot_view_webhook_status(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner30b_helper@test.ci")
        token, _ = _make_driver_token(client, db, owner_token, "web30b")
        res = client.get("/api/v1/webhook/status", headers=_headers(token))
        assert res.status_code == 403


# ── US-029: Webhook trigger ───────────────────────────────────────────────────


class TestWebhookTrigger:
    def test_trigger_without_configured_url_returns_400(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "web29a@test.ci")

        with patch("app.core.config.settings.WEBHOOK_URL", ""):
            res = client.post("/api/v1/webhook/trigger", headers=_headers(token))
        assert res.status_code == 400

    def test_trigger_with_configured_url_succeeds(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "web29b@test.ci")

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch(
            "app.core.config.settings.WEBHOOK_URL", "https://hook.example.com"
        ), patch("app.services.webhook_service.httpx.post", return_value=mock_response):
            res = client.post("/api/v1/webhook/trigger", headers=_headers(token))

        assert res.status_code == 200
        data = res.json()
        assert data["configured"] is True
        assert data["last_status_code"] == 200
        assert data["last_sent_at"] is not None

    def test_trigger_stores_state_in_db(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "web29c@test.ci")
        owner_id = _get_user_id(token)

        mock_response = MagicMock()
        mock_response.status_code = 201

        with patch(
            "app.core.config.settings.WEBHOOK_URL", "https://hook.example.com"
        ), patch("app.services.webhook_service.httpx.post", return_value=mock_response):
            client.post("/api/v1/webhook/trigger", headers=_headers(token))

        from app.models.webhook_state import WebhookState

        state = db.query(WebhookState).filter(WebhookState.owner_id == owner_id).first()
        assert state is not None
        assert state.last_status_code == 201

    def test_unauthenticated_cannot_trigger_webhook(self, client, db):
        res = client.post("/api/v1/webhook/trigger")
        assert res.status_code == 403


# ── Unit: ai_report_service helpers ──────────────────────────────────────────


class TestAiReportServiceUnit:
    def test_monthly_counter_resets_on_new_month(self, client, db):
        _seed_plans(db)
        from datetime import date
        from app.models.report_schedule import ReportSchedule
        from app.services.ai_report_service import _maybe_reset_monthly_counter

        token = _register_and_verify(client, db, "unit33x@test.ci")
        owner_id = _get_user_id(token)

        # Simulate a schedule with usage from last month
        last_month = date(2026, 3, 1)
        sched = ReportSchedule(
            owner_id=owner_id, ai_reports_used_month=5, usage_reset_at=last_month
        )
        db.add(sched)
        db.commit()

        _maybe_reset_monthly_counter(db, sched)

        assert sched.ai_reports_used_month == 0
        assert sched.usage_reset_at == date.today()

    def test_cadence_elapsed_returns_true_when_never_sent(self):
        from app.models.report_schedule import ReportSchedule
        from app.services.ai_report_service import _cadence_elapsed

        sched = ReportSchedule(owner_id=1, frequency="weekly", last_sent_at=None)
        assert _cadence_elapsed(sched, datetime.now(timezone.utc)) is True

    def test_cadence_elapsed_weekly_not_yet(self):
        from app.models.report_schedule import ReportSchedule
        from app.services.ai_report_service import _cadence_elapsed

        sent_3_days_ago = datetime(2026, 4, 8, tzinfo=timezone.utc)
        sched = ReportSchedule(
            owner_id=1, frequency="weekly", last_sent_at=sent_3_days_ago
        )
        now = datetime(2026, 4, 11, tzinfo=timezone.utc)
        assert _cadence_elapsed(sched, now) is False

    def test_cadence_elapsed_weekly_due(self):
        from app.models.report_schedule import ReportSchedule
        from app.services.ai_report_service import _cadence_elapsed

        sent_8_days_ago = datetime(2026, 4, 3, tzinfo=timezone.utc)
        sched = ReportSchedule(
            owner_id=1, frequency="weekly", last_sent_at=sent_8_days_ago
        )
        now = datetime(2026, 4, 11, tzinfo=timezone.utc)
        assert _cadence_elapsed(sched, now) is True


# ── Unit: webhook_service helpers ─────────────────────────────────────────────


class TestWebhookServiceUnit:
    def test_dispatch_returns_zero_on_timeout(self):
        import httpx
        from app.services.webhook_service import _dispatch

        with patch(
            "app.services.webhook_service.httpx.post",
            side_effect=httpx.TimeoutException("timeout"),
        ):
            with patch(
                "app.core.config.settings.WEBHOOK_URL", "https://hook.example.com"
            ):
                result = _dispatch({"event": "test"})
        assert result == 0

    def test_get_webhook_status_returns_none_when_no_record(self, db):
        _seed_plans(db)
        from app.services.webhook_service import get_webhook_status

        result = get_webhook_status(db, owner_id=99999)
        assert result is None
