"""
Tests for Sprint 4 maintenance & alert engine stories:
  US-015 — Manage maintenance records
  US-016 — Oil change tracking by mileage
  US-026 — Maintenance & compliance alerts
  US-027 — Abnormal fuel consumption detection
  US-028 — Monthly cost spike detection
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


def _get_driver_id(driver_token):
    from app.core.security import decode_access_token
    return int(decode_access_token(driver_token)["sub"])


def _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id):
    driver_id = _get_driver_id(driver_token)
    client.post(f"/api/v1/vehicles/{vehicle_id}/drivers", json={"driver_id": driver_id}, headers=owner_headers)
    client.post("/api/v1/driver/activate", json={"vehicle_id": vehicle_id}, headers=driver_headers)


def _add_fuel_entry(db, vehicle_id, driver_id, odometer, litres, amount, entry_date=None, created_at=None):
    """Insert a fuel entry directly into the DB for test setup."""
    distance = None
    consumption = None
    if entry_date is None:
        entry_date = date.today()
    entry = FuelEntry(
        vehicle_id=vehicle_id,
        driver_id=driver_id,
        date=entry_date,
        odometer_km=odometer,
        quantity_litres=litres,
        amount_fcfa=amount,
        distance_km=distance,
        consumption_per_100km=consumption,
    )
    if created_at is not None:
        entry.created_at = created_at
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def owner_token(client, db):
    _seed_plans(db)
    return _register_and_verify(client, db, "owner@maint.ci", "OWNER")


@pytest.fixture()
def driver_token(client, db):
    return _register_and_verify(client, db, "driver@maint.ci", "DRIVER")


@pytest.fixture()
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture()
def driver_headers(driver_token):
    return {"Authorization": f"Bearer {driver_token}"}


# ── US-015: Manage maintenance records ───────────────────────────────────────

def test_get_maintenance_auto_creates_record(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-001-CI")
    res = client.get(f"/api/v1/vehicles/{vid}/maintenance", headers=owner_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["vehicle_id"] == vid
    assert data["last_oil_change_km"] is None
    assert data["insurance_expiry"] is None
    assert data["inspection_expiry"] is None


def test_get_maintenance_idempotent(client, db, owner_headers):
    """Calling GET twice should not create two records."""
    vid = _create_vehicle(client, owner_headers, "MT-002-CI")
    client.get(f"/api/v1/vehicles/{vid}/maintenance", headers=owner_headers)
    client.get(f"/api/v1/vehicles/{vid}/maintenance", headers=owner_headers)
    count = db.query(Maintenance).filter(Maintenance.vehicle_id == vid).count()
    assert count == 1


def test_update_maintenance_fields(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-003-CI")
    expiry = str(date.today() + timedelta(days=60))
    res = client.put(f"/api/v1/vehicles/{vid}/maintenance", json={
        "last_oil_change_km": 12000,
        "insurance_expiry": expiry,
    }, headers=owner_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["last_oil_change_km"] == 12000
    assert data["insurance_expiry"] == expiry
    assert data["inspection_expiry"] is None


def test_update_maintenance_partial(client, db, owner_headers):
    """Only sent fields are updated; existing fields preserved."""
    vid = _create_vehicle(client, owner_headers, "MT-004-CI")
    expiry = str(date.today() + timedelta(days=90))
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"insurance_expiry": expiry}, headers=owner_headers)
    res = client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"last_oil_change_km": 5000}, headers=owner_headers)
    data = res.json()["data"]
    assert data["last_oil_change_km"] == 5000
    assert data["insurance_expiry"] == expiry  # preserved


def test_maintenance_404_for_unknown_vehicle(client, db, owner_headers):
    res = client.get("/api/v1/vehicles/99999/maintenance", headers=owner_headers)
    assert res.status_code == 404


# ── US-026: Compliance date alerts ───────────────────────────────────────────

def test_no_alerts_when_no_maintenance(client, db, owner_headers):
    _create_vehicle(client, owner_headers, "MT-005-CI")
    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_critical_alert_for_expired_insurance(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-006-CI")
    expired = str(date.today() - timedelta(days=5))
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"insurance_expiry": expired}, headers=owner_headers)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    alerts = res.json()["data"]
    ins = [a for a in alerts if a["type"] == "insurance_expiry"]
    assert len(ins) == 1
    assert ins[0]["severity"] == "critical"


def test_warning_alert_for_upcoming_insurance(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-007-CI")
    soon = str(date.today() + timedelta(days=15))
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"insurance_expiry": soon}, headers=owner_headers)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    alerts = res.json()["data"]
    ins = [a for a in alerts if a["type"] == "insurance_expiry"]
    assert len(ins) == 1
    assert ins[0]["severity"] == "warning"


def test_no_alert_when_insurance_far(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-008-CI")
    far = str(date.today() + timedelta(days=60))
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"insurance_expiry": far}, headers=owner_headers)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    alerts = res.json()["data"]
    assert not any(a["type"] == "insurance_expiry" for a in alerts)


def test_critical_alert_for_expired_inspection(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-009-CI")
    expired = str(date.today() - timedelta(days=1))
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"inspection_expiry": expired}, headers=owner_headers)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    alerts = res.json()["data"]
    ins = [a for a in alerts if a["type"] == "inspection_expiry"]
    assert len(ins) == 1
    assert ins[0]["severity"] == "critical"


def test_paused_vehicle_has_no_alerts(client, db, owner_headers):
    vid = _create_vehicle(client, owner_headers, "MT-010-CI")
    expired = str(date.today() - timedelta(days=10))
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"insurance_expiry": expired}, headers=owner_headers)
    client.post(f"/api/v1/vehicles/{vid}/pause", headers=owner_headers)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["vehicle_id"] == vid for a in res.json()["data"])


# ── US-016: Oil change alert ──────────────────────────────────────────────────

def test_no_oil_alert_without_last_oil_change_km(client, db, owner_headers, driver_token, driver_headers):
    vid = _create_vehicle(client, owner_headers, "MT-011-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)
    _add_fuel_entry(db, vid, driver_id, 10600, 40, 24000)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["type"] == "oil_change" for a in res.json()["data"])


def test_warning_oil_alert_between_400_and_500(client, db, owner_headers, driver_token, driver_headers):
    vid = _create_vehicle(client, owner_headers, "MT-012-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"last_oil_change_km": 10000}, headers=owner_headers)
    _add_fuel_entry(db, vid, driver_id, 10450, 40, 24000)  # 450 km since oil change

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    alerts = [a for a in res.json()["data"] if a["type"] == "oil_change"]
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "warning"


def test_critical_oil_alert_above_500(client, db, owner_headers, driver_token, driver_headers):
    vid = _create_vehicle(client, owner_headers, "MT-013-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"last_oil_change_km": 10000}, headers=owner_headers)
    _add_fuel_entry(db, vid, driver_id, 10550, 40, 24000)  # 550 km since oil change

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    alerts = [a for a in res.json()["data"] if a["type"] == "oil_change"]
    assert len(alerts) == 1
    assert alerts[0]["severity"] == "critical"


def test_oil_alert_clears_after_update(client, db, owner_headers, driver_token, driver_headers):
    vid = _create_vehicle(client, owner_headers, "MT-014-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"last_oil_change_km": 10000}, headers=owner_headers)
    _add_fuel_entry(db, vid, driver_id, 10600, 40, 24000)  # 600 km since oil change → critical

    # Reset oil change
    client.put(f"/api/v1/vehicles/{vid}/maintenance", json={"last_oil_change_km": 10600}, headers=owner_headers)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["type"] == "oil_change" for a in res.json()["data"])


# ── US-027: Consumption anomaly ───────────────────────────────────────────────

def test_no_anomaly_with_fewer_than_2_entries(client, db, owner_headers, driver_token, driver_headers):
    vid = _create_vehicle(client, owner_headers, "MT-015-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)
    _add_fuel_entry(db, vid, driver_id, 10500, 40, 24000)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["type"] == "consumption_anomaly" for a in res.json()["data"])


def test_consumption_anomaly_detected(client, db, owner_headers, driver_token, driver_headers):
    """3 historical entries averaging 8 L/100km, latest at 12 L/100km (50% deviation)."""
    vid = _create_vehicle(client, owner_headers, "MT-016-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    # Insert historical entries directly with known consumption values
    for i, (odo, litres) in enumerate([(10500, 40), (11000, 40), (11500, 40)]):
        e = _add_fuel_entry(db, vid, driver_id, odo, litres, 24000)
        distance = 500
        consumption = litres / distance * 100  # 8.0 L/100km
        e.distance_km = distance
        e.consumption_per_100km = consumption
    db.commit()

    # Latest entry: much higher consumption — 12 L/100km
    latest = _add_fuel_entry(db, vid, driver_id, 12100, 72, 43000)
    latest.distance_km = 600
    latest.consumption_per_100km = 12.0
    db.commit()

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    anomalies = [a for a in res.json()["data"] if a["type"] == "consumption_anomaly"]
    assert len(anomalies) == 1
    assert anomalies[0]["vehicle_id"] == vid


def test_no_anomaly_within_20_percent(client, db, owner_headers, driver_token, driver_headers):
    """Historical avg 8 L/100km, latest 8.5 — within 20%."""
    vid = _create_vehicle(client, owner_headers, "MT-017-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    for odo in [10500, 11000]:
        e = _add_fuel_entry(db, vid, driver_id, odo, 40, 24000)
        e.distance_km = 500
        e.consumption_per_100km = 8.0
    db.commit()

    latest = _add_fuel_entry(db, vid, driver_id, 11500, 42.5, 25000)
    latest.distance_km = 500
    latest.consumption_per_100km = 8.5
    db.commit()

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["type"] == "consumption_anomaly" for a in res.json()["data"])


# ── US-028: Monthly cost spike ────────────────────────────────────────────────

def test_no_cost_spike_without_last_month_data(client, db, owner_headers, driver_token, driver_headers):
    vid = _create_vehicle(client, owner_headers, "MT-018-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)
    _add_fuel_entry(db, vid, driver_id, 10500, 40, 24000, entry_date=date.today())

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["type"] == "cost_spike" for a in res.json()["data"])


def test_cost_spike_detected(client, db, owner_headers, driver_token, driver_headers):
    """Last month: 20,000 FCFA. This month: 30,000 FCFA (50% spike)."""
    vid = _create_vehicle(client, owner_headers, "MT-019-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    today = date.today()
    last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    _add_fuel_entry(db, vid, driver_id, 10200, 30, 20000, entry_date=last_month)
    _add_fuel_entry(db, vid, driver_id, 10500, 45, 30000, entry_date=today)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    spikes = [a for a in res.json()["data"] if a["type"] == "cost_spike"]
    assert len(spikes) == 1
    assert spikes[0]["vehicle_id"] == vid


def test_no_cost_spike_within_30_percent(client, db, owner_headers, driver_token, driver_headers):
    """Last month: 20,000 FCFA. This month: 24,000 FCFA (20% — below threshold)."""
    vid = _create_vehicle(client, owner_headers, "MT-020-CI", mileage=10000)
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vid)
    driver_id = _get_driver_id(driver_token)

    today = date.today()
    last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)

    _add_fuel_entry(db, vid, driver_id, 10200, 30, 20000, entry_date=last_month)
    _add_fuel_entry(db, vid, driver_id, 10500, 36, 24000, entry_date=today)

    res = client.get("/api/v1/owner/alerts", headers=owner_headers)
    assert not any(a["type"] == "cost_spike" for a in res.json()["data"])
