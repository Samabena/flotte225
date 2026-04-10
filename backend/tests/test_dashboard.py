"""
Tests for Sprint 5 owner dashboard stories:
  US-017 — Fleet financial summary & charts
  US-018 — Fleet consumption indicators
  US-019 — Driver status panel
  US-020 — Alerts, anomalies & compliance on dashboard
  US-025 — Filter activity log
"""
import pytest
from datetime import date, timedelta, datetime, timezone
from unittest.mock import patch

from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan, OwnerSubscription
from app.models.fuel_entry import FuelEntry
from app.models.maintenance import Maintenance
from app.models.vehicle_driver import VehicleDriver


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_plans(db):
    from scripts.seed import PLANS
    for plan_data in PLANS:
        if not db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_data["name"]).first():
            db.add(SubscriptionPlan(**plan_data))
    db.commit()


def _register_and_verify(client, db, email, role="OWNER"):
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/register", json={
            "full_name": "Test User",
            "email": email,
            "password": "Password1",
            "role": role,
        })
    otp = db.query(OtpCode).filter(OtpCode.purpose == "EMAIL_VERIFY").order_by(OtpCode.id.desc()).first()
    client.post("/api/v1/auth/verify-email", json={"email": email, "code": otp.code})
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password1"})
    return res.json()["access_token"]


def _create_vehicle(client, owner_headers, plate="MT-001-CI", mileage=10000):
    return client.post("/api/v1/vehicles", json={
        "name": "Véhicule Test",
        "brand": "Toyota",
        "model": "HiLux",
        "license_plate": plate,
        "fuel_type": "Diesel",
        "initial_mileage": mileage,
    }, headers=owner_headers).json()["data"]["id"]


def _get_user_id(token):
    from app.core.security import decode_access_token
    return int(decode_access_token(token)["sub"])


def _add_fuel(db, vehicle_id, driver_id, odometer, amount, consumption=None):
    entry = FuelEntry(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        date=date.today(),
        odometer_km=odometer,
        quantity_litres=40,
        amount_fcfa=amount,
        distance_km=None,
        consumption_per_100km=consumption,
    )
    db.add(entry)
    db.commit()
    return entry


# ── US-017 / US-018 / US-019 / US-020: Dashboard endpoint ────────────────────

class TestDashboardEmpty:
    """Dashboard with no fleet data returns zero values and empty lists."""

    def test_dashboard_returns_200_for_owner(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner@test.ci")
        res = client.get("/api/v1/dashboard/owner", headers={"Authorization": f"Bearer {owner_token}"})
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_dashboard_financial_zero_when_no_entries(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner2@test.ci")
        res = client.get("/api/v1/dashboard/owner", headers={"Authorization": f"Bearer {owner_token}"})
        data = res.json()["data"]
        assert float(data["financial"]["total_spend_fcfa"]) == 0
        assert data["financial"]["spend_per_vehicle"] == []
        assert data["financial"]["monthly_trend"] == []

    def test_dashboard_consumption_lists_vehicles_with_no_entries(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner3@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        _create_vehicle(client, owner_headers, plate="MT-010-CI")
        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        data = res.json()["data"]
        assert len(data["consumption"]) == 1
        assert data["consumption"][0]["avg_consumption_per_100km"] is None
        assert data["consumption"][0]["entry_count"] == 0

    def test_dashboard_drivers_empty_when_none_assigned(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner4@test.ci")
        res = client.get("/api/v1/dashboard/owner", headers={"Authorization": f"Bearer {owner_token}"})
        assert res.json()["data"]["drivers"] == []

    def test_dashboard_alerts_empty_when_no_maintenance(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner5@test.ci")
        res = client.get("/api/v1/dashboard/owner", headers={"Authorization": f"Bearer {owner_token}"})
        assert res.json()["data"]["alerts"] == []

    def test_driver_cannot_access_owner_dashboard(self, client, db):
        _seed_plans(db)
        driver_token = _register_and_verify(client, db, "driver1@test.ci", role="DRIVER")
        res = client.get("/api/v1/dashboard/owner", headers={"Authorization": f"Bearer {driver_token}"})
        assert res.status_code == 403


class TestDashboardFinancial:
    """US-017 — Financial summary with fuel data."""

    def test_total_spend_sums_all_vehicles(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "fin1@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        owner_id = _get_user_id(owner_token)
        driver_token = _register_and_verify(client, db, "findrvr1@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        v1 = _create_vehicle(client, owner_headers, plate="FIN-001-CI")
        v2 = _create_vehicle(client, owner_headers, plate="FIN-002-CI")

        _add_fuel(db, v1, driver_id, 10100, 50000)
        _add_fuel(db, v1, driver_id, 10200, 30000)
        _add_fuel(db, v2, driver_id, 20100, 20000)

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        financial = res.json()["data"]["financial"]
        assert float(financial["total_spend_fcfa"]) == 100000

    def test_spend_per_vehicle_is_grouped(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "fin2@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        driver_token = _register_and_verify(client, db, "findrvr2@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        v1 = _create_vehicle(client, owner_headers, plate="FIN-003-CI")
        _add_fuel(db, v1, driver_id, 10100, 40000)
        _add_fuel(db, v1, driver_id, 10200, 60000)

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        spv = res.json()["data"]["financial"]["spend_per_vehicle"]
        assert len(spv) == 1
        assert float(spv[0]["spend_fcfa"]) == 100000

    def test_monthly_trend_aggregates_by_month(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "fin3@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        driver_token = _register_and_verify(client, db, "findrvr3@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        v1 = _create_vehicle(client, owner_headers, plate="FIN-004-CI")
        # All entries today — should produce one month entry
        _add_fuel(db, v1, driver_id, 10100, 25000)
        _add_fuel(db, v1, driver_id, 10200, 35000)

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        trend = res.json()["data"]["financial"]["monthly_trend"]
        assert len(trend) == 1
        assert float(trend[0]["spend_fcfa"]) == 60000


class TestDashboardConsumption:
    """US-018 — Consumption indicators per vehicle."""

    def test_avg_consumption_computed_from_entries(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "cons1@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        driver_token = _register_and_verify(client, db, "consdrvr1@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        v1 = _create_vehicle(client, owner_headers, plate="CON-001-CI")
        _add_fuel(db, v1, driver_id, 10100, 50000, consumption=8.5)
        _add_fuel(db, v1, driver_id, 10200, 50000, consumption=9.5)

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        consumption = res.json()["data"]["consumption"]
        assert len(consumption) == 1
        assert float(consumption[0]["avg_consumption_per_100km"]) == pytest.approx(9.0, abs=0.01)
        assert consumption[0]["entry_count"] == 2

    def test_null_consumption_when_no_entries(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "cons2@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        _create_vehicle(client, owner_headers, plate="CON-002-CI")

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        consumption = res.json()["data"]["consumption"]
        assert consumption[0]["avg_consumption_per_100km"] is None


class TestDashboardDrivers:
    """US-019 — Driver status panel."""

    def test_assigned_driver_appears_in_panel(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "drv1@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        driver_token = _register_and_verify(client, db, "drvr11@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        v1 = _create_vehicle(client, owner_headers, plate="DRV-001-CI")
        client.post(f"/api/v1/vehicles/{v1}/drivers", json={"driver_id": driver_id}, headers=owner_headers)

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        drivers = res.json()["data"]["drivers"]
        assert len(drivers) == 1
        assert drivers[0]["driver_id"] == driver_id
        assert drivers[0]["driving_status"] is False

    def test_active_driver_shows_vehicle(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "drv2@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        driver_token = _register_and_verify(client, db, "drvr22@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        v1 = _create_vehicle(client, owner_headers, plate="DRV-002-CI")
        client.post(f"/api/v1/vehicles/{v1}/drivers", json={"driver_id": driver_id}, headers=owner_headers)
        client.post("/api/v1/driver/activate", json={"vehicle_id": v1}, headers=driver_headers)

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        drivers = res.json()["data"]["drivers"]
        assert drivers[0]["driving_status"] is True
        assert drivers[0]["active_vehicle_id"] == v1
        assert drivers[0]["active_vehicle_name"] is not None


class TestDashboardAlerts:
    """US-020 — Alerts & anomalies on dashboard (uses alert_service via dashboard)."""

    def test_expired_insurance_appears_as_critical_alert(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "alrt1@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}

        v1 = _create_vehicle(client, owner_headers, plate="ALT-001-CI")
        db.add(Maintenance(
            vehicle_id=v1,
            insurance_expiry=date.today() - timedelta(days=5),
        ))
        db.commit()

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        alerts = res.json()["data"]["alerts"]
        critical = [a for a in alerts if a["type"] == "insurance_expiry" and a["severity"] == "critical"]
        assert len(critical) == 1

    def test_no_alerts_without_maintenance_record(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "alrt2@test.ci")
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        _create_vehicle(client, owner_headers, plate="ALT-002-CI")

        res = client.get("/api/v1/dashboard/owner", headers=owner_headers)
        assert res.json()["data"]["alerts"] == []


# ── US-025: Filter activity log ───────────────────────────────────────────────

class TestActivityLogFilter:
    """US-025 — Filter activity log by driver and/or vehicle."""

    def _setup(self, client, db, owner_email, driver_email, plate):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, owner_email)
        owner_headers = {"Authorization": f"Bearer {owner_token}"}
        driver_token = _register_and_verify(client, db, driver_email, role="DRIVER")
        driver_id = _get_user_id(driver_token)
        driver_headers = {"Authorization": f"Bearer {driver_token}"}

        v1 = _create_vehicle(client, owner_headers, plate=plate)
        client.post(f"/api/v1/vehicles/{v1}/drivers", json={"driver_id": driver_id}, headers=owner_headers)
        client.post("/api/v1/driver/activate", json={"vehicle_id": v1}, headers=driver_headers)

        # Submit a fuel entry to generate an activity log
        client.post("/api/v1/fuel", json={
            "vehicle_id": v1,
            "date": str(date.today()),
            "odometer_km": 10100,
            "quantity_litres": "40.00",
            "amount_fcfa": "50000.00",
        }, headers=driver_headers)

        return owner_headers, driver_id, v1

    def test_unfiltered_returns_all_logs(self, client, db):
        owner_headers, driver_id, v1 = self._setup(
            client, db, "log1@test.ci", "logd1@test.ci", "LOG-001-CI"
        )
        res = client.get("/api/v1/owner/activity-logs", headers=owner_headers)
        assert res.status_code == 200
        assert len(res.json()["data"]) >= 1

    def test_filter_by_driver_id(self, client, db):
        owner_headers, driver_id, v1 = self._setup(
            client, db, "log2@test.ci", "logd2@test.ci", "LOG-002-CI"
        )
        res = client.get(f"/api/v1/owner/activity-logs?driver_id={driver_id}", headers=owner_headers)
        data = res.json()["data"]
        assert all(log["driver_id"] == driver_id for log in data)

    def test_filter_by_vehicle_id(self, client, db):
        owner_headers, driver_id, v1 = self._setup(
            client, db, "log3@test.ci", "logd3@test.ci", "LOG-003-CI"
        )
        res = client.get(f"/api/v1/owner/activity-logs?vehicle_id={v1}", headers=owner_headers)
        data = res.json()["data"]
        assert all(log["vehicle_id"] == v1 for log in data)

    def test_filter_by_unknown_driver_returns_empty(self, client, db):
        owner_headers, driver_id, v1 = self._setup(
            client, db, "log4@test.ci", "logd4@test.ci", "LOG-004-CI"
        )
        res = client.get("/api/v1/owner/activity-logs?driver_id=99999", headers=owner_headers)
        assert res.json()["data"] == []

    def test_pagination_limit_respected(self, client, db):
        owner_headers, driver_id, v1 = self._setup(
            client, db, "log5@test.ci", "logd5@test.ci", "LOG-005-CI"
        )
        res = client.get("/api/v1/owner/activity-logs?limit=1", headers=owner_headers)
        assert len(res.json()["data"]) <= 1
