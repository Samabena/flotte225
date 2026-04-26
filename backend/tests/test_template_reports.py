"""
Tests for the deterministic template report endpoints (POST /reports/template/*).
Covers fleet-wide and per-driver PDF generation, cross-tenant isolation,
date-range validation, and empty-window rendering.
"""

from datetime import date, timedelta
from unittest.mock import patch

from app.models.fuel_entry import FuelEntry
from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan


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
                "full_name": "Test Owner",
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


def _get_user_id(token):
    from app.core.security import decode_access_token

    return int(decode_access_token(token)["sub"])


def _create_driver_in_db(db, owner_id, username, full_name="Aïcha Touré"):
    from app.models.user import User
    from app.core.security import hash_password

    driver = User(
        full_name=full_name,
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


def _create_vehicle(client, owner_headers, plate, name="Véhicule Test"):
    return client.post(
        "/api/v1/vehicles",
        json={
            "name": name,
            "brand": "Toyota",
            "model": "HiLux",
            "license_plate": plate,
            "fuel_type": "Diesel",
            "initial_mileage": 10000,
        },
        headers=owner_headers,
    ).json()["data"]["id"]


def _add_fuel(
    db, vehicle_id, driver_id, odometer, amount, on_date=None, consumption=8.5
):
    entry = FuelEntry(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        date=on_date or date.today(),
        odometer_km=odometer,
        quantity_litres=40,
        amount_fcfa=amount,
        distance_km=100,
        consumption_per_100km=consumption,
    )
    db.add(entry)
    db.commit()
    return entry


# ── Fleet template report ─────────────────────────────────────────────────────


class TestFleetTemplateReport:
    def test_returns_pdf_for_owner_with_fleet(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "fleet1@test.ci")
        owner_id = _get_user_id(token)
        headers = _headers(token)

        v_id = _create_vehicle(client, headers, "FLT-001-CI", "Camion 1")
        driver = _create_driver_in_db(db, owner_id, "drv_fleet1")
        _add_fuel(
            db, v_id, driver.id, 10100, 50000, on_date=date.today() - timedelta(days=2)
        )
        _add_fuel(
            db, v_id, driver.id, 10250, 35000, on_date=date.today() - timedelta(days=1)
        )

        res = client.post(
            "/api/v1/reports/template/fleet",
            headers=headers,
            json={
                "date_from": (date.today() - timedelta(days=30)).isoformat(),
                "date_to": date.today().isoformat(),
            },
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert "rapport-flotte-" in res.headers["content-disposition"]
        assert res.content[:4] == b"%PDF"

    def test_empty_range_renders_gracefully(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "fleet2@test.ci")
        headers = _headers(token)

        # Owner with no vehicles, no fuel — endpoint should still produce a PDF
        res = client.post(
            "/api/v1/reports/template/fleet",
            headers=headers,
            json={
                "date_from": (date.today() - timedelta(days=7)).isoformat(),
                "date_to": date.today().isoformat(),
            },
        )
        assert res.status_code == 200
        assert res.content[:4] == b"%PDF"

    def test_defaults_to_last_30_days_when_body_empty(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "fleet3@test.ci")
        headers = _headers(token)

        res = client.post("/api/v1/reports/template/fleet", headers=headers, json={})
        assert res.status_code == 200
        assert res.content[:4] == b"%PDF"

    def test_invalid_date_range_rejected(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "fleet4@test.ci")
        headers = _headers(token)

        res = client.post(
            "/api/v1/reports/template/fleet",
            headers=headers,
            json={
                "date_from": date.today().isoformat(),
                "date_to": (date.today() - timedelta(days=5)).isoformat(),
            },
        )
        assert res.status_code == 422

    def test_unauthenticated_blocked(self, client, db):
        res = client.post("/api/v1/reports/template/fleet", json={})
        assert res.status_code == 403  # missing bearer


# ── Driver template report ───────────────────────────────────────────────────


class TestDriverTemplateReport:
    def test_returns_pdf_for_owned_driver(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "drv1@test.ci")
        owner_id = _get_user_id(token)
        headers = _headers(token)

        v_id = _create_vehicle(client, headers, "DRV-001-CI", "Voiture A")
        driver = _create_driver_in_db(db, owner_id, "drv_one", full_name="Konaté Issa")
        _add_fuel(
            db, v_id, driver.id, 10100, 22000, on_date=date.today() - timedelta(days=1)
        )

        res = client.post(
            f"/api/v1/reports/template/driver/{driver.id}",
            headers=headers,
            json={
                "date_from": (date.today() - timedelta(days=30)).isoformat(),
                "date_to": date.today().isoformat(),
            },
        )
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert f"rapport-conducteur-{driver.id}-" in res.headers["content-disposition"]
        assert res.content[:4] == b"%PDF"

    def test_cross_tenant_driver_blocked(self, client, db):
        _seed_plans(db)
        # Owner A creates a driver
        owner_a_token = _register_and_verify(client, db, "owA@test.ci")
        owner_a_id = _get_user_id(owner_a_token)
        driver_a = _create_driver_in_db(db, owner_a_id, "drv_owA", full_name="Driver A")

        # Owner B tries to fetch driver A's report
        owner_b_token = _register_and_verify(client, db, "owB@test.ci")
        res = client.post(
            f"/api/v1/reports/template/driver/{driver_a.id}",
            headers=_headers(owner_b_token),
            json={},
        )
        assert res.status_code == 404
        assert "Conducteur introuvable" in res.json()["detail"]

    def test_unknown_driver_returns_404(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "drv_missing@test.ci")
        res = client.post(
            "/api/v1/reports/template/driver/999999",
            headers=_headers(token),
            json={},
        )
        assert res.status_code == 404

    def test_driver_report_with_no_entries_still_renders(self, client, db):
        _seed_plans(db)
        token = _register_and_verify(client, db, "drv_empty@test.ci")
        owner_id = _get_user_id(token)
        driver = _create_driver_in_db(db, owner_id, "drv_empty_user", full_name="Vide")

        res = client.post(
            f"/api/v1/reports/template/driver/{driver.id}",
            headers=_headers(token),
            json={
                "date_from": (date.today() - timedelta(days=7)).isoformat(),
                "date_to": date.today().isoformat(),
            },
        )
        assert res.status_code == 200
        assert res.content[:4] == b"%PDF"
