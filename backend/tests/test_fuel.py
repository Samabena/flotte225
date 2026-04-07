"""
Tests for Sprint 3 fuel entry & audit log stories:
  US-010 — Submit a fuel entry
  US-011 — View my fuel entry history (driver)
  US-012 — Edit a fuel entry (within 24h)
  US-013 — Delete a fuel entry (within 24h)
  US-014 — Owner views fleet fuel entries
  US-024 — Automatic activity logging
"""
import pytest
from datetime import date, datetime, timezone, timedelta
from unittest.mock import patch

from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan, OwnerSubscription
from app.models.fuel_entry import FuelEntry
from app.models.vehicle_driver import VehicleDriver


# ── Fixtures & helpers ────────────────────────────────────────────────────────

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


VEHICLE_PAYLOAD = {
    "name": "Camion Fuel",
    "brand": "Toyota",
    "model": "HiLux",
    "year": 2020,
    "license_plate": "FU-001-CI",
    "fuel_type": "Diesel",
    "initial_mileage": 10000,
}

FUEL_PAYLOAD = {
    "date": str(date.today()),
    "odometer_km": 10500,
    "quantity_litres": "45.00",
    "amount_fcfa": "27000.00",
}


@pytest.fixture()
def owner_token(client, db):
    _seed_plans(db)
    return _register_and_verify(client, db, "owner@fuel.ci", "OWNER")


@pytest.fixture()
def driver_token(client, db):
    return _register_and_verify(client, db, "driver@fuel.ci", "DRIVER")


@pytest.fixture()
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture()
def driver_headers(driver_token):
    return {"Authorization": f"Bearer {driver_token}"}


def _create_vehicle(client, owner_headers, payload=None):
    p = {**VEHICLE_PAYLOAD, **(payload or {})}
    return client.post("/api/v1/vehicles", json=p, headers=owner_headers)


def _get_driver_id(client, db, driver_token):
    from app.models.user import User
    from app.core.security import decode_access_token
    payload = decode_access_token(driver_token)
    return int(payload["sub"])


def _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id):
    """Assign the driver to a vehicle and activate them."""
    driver_id = _get_driver_id(client, db, driver_token)
    client.post(f"/api/v1/vehicles/{vehicle_id}/drivers", json={"driver_id": driver_id}, headers=owner_headers)
    client.post("/api/v1/driver/activate", json={"vehicle_id": vehicle_id}, headers=driver_headers)
    return driver_id


# ── US-010: Submit a fuel entry ───────────────────────────────────────────────

def test_submit_fuel_entry_success(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers)
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["odometer_km"] == 10500
    assert data["distance_km"] == 500
    assert data["vehicle_id"] == vehicle_id


def test_submit_calculates_consumption(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-002-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    # initial_mileage=10000, odometer=10500 → distance=500, consumption=(45/500)*100=9.0
    res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert float(data["consumption_per_100km"]) == pytest.approx(9.0, abs=0.01)


def test_submit_rejected_when_driver_inactive(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-003-CI"})
    vehicle_id = veh.json()["data"]["id"]
    driver_id = _get_driver_id(client, db, driver_token)
    # Assign but do NOT activate
    client.post(f"/api/v1/vehicles/{vehicle_id}/drivers", json={"driver_id": driver_id}, headers=owner_headers)

    res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    assert res.status_code == 403


def test_submit_rejected_when_wrong_vehicle(client, db, owner_headers, driver_token, driver_headers):
    # Driver activates on vehicle 1 but tries to submit for vehicle 2
    veh1 = _create_vehicle(client, owner_headers, {"license_plate": "FU-010-CI"})
    veh2 = _create_vehicle(client, owner_headers, {"license_plate": "FU-011-CI"})
    vid1 = veh1.json()["data"]["id"]
    vid2 = veh2.json()["data"]["id"]

    driver_id = _get_driver_id(client, db, driver_token)
    client.post(f"/api/v1/vehicles/{vid1}/drivers", json={"driver_id": driver_id}, headers=owner_headers)
    client.post(f"/api/v1/vehicles/{vid2}/drivers", json={"driver_id": driver_id}, headers=owner_headers)
    client.post("/api/v1/driver/activate", json={"vehicle_id": vid1}, headers=driver_headers)

    res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vid2}, headers=driver_headers)
    assert res.status_code == 403


def test_submit_rejected_when_not_assigned(client, db, owner_headers, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-004-CI"})
    vehicle_id = veh.json()["data"]["id"]
    # Do not assign driver at all

    res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    assert res.status_code == 403


def test_submit_rejected_when_odometer_not_greater(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-005-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    # First entry at 10500
    client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)

    # Deactivate and reactivate so we can submit another
    client.post("/api/v1/driver/deactivate", headers=driver_headers)
    client.post("/api/v1/driver/activate", json={"vehicle_id": vehicle_id}, headers=driver_headers)

    # Same odometer — should fail
    res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    assert res.status_code == 422

    # Lower odometer — should also fail
    res2 = client.post(
        "/api/v1/fuel",
        json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id, "odometer_km": 9000},
        headers=driver_headers,
    )
    assert res2.status_code == 422


# ── US-011: View my fuel entry history ───────────────────────────────────────

def test_list_driver_entries_empty(client, driver_headers):
    res = client.get("/api/v1/fuel", headers=driver_headers)
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_list_driver_entries_returns_last_10(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-006-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    # Insert 12 entries directly into DB
    from app.models.user import User
    from app.core.security import decode_access_token
    payload = decode_access_token(driver_token)
    driver_id = int(payload["sub"])
    for i in range(12):
        db.add(FuelEntry(
            vehicle_id=vehicle_id,
            driver_id=driver_id,
            date=date.today(),
            odometer_km=10100 + i * 100,
            quantity_litres=40,
            amount_fcfa=24000,
            distance_km=100,
            consumption_per_100km=40.0,
        ))
    db.commit()

    res = client.get("/api/v1/fuel", headers=driver_headers)
    assert res.status_code == 200
    assert len(res.json()["data"]) == 10


# ── US-012: Edit a fuel entry (within 24h) ───────────────────────────────────

def test_edit_fuel_entry_success(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-007-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    res = client.patch(f"/api/v1/fuel/{entry_id}", json={"amount_fcfa": "30000.00"}, headers=driver_headers)
    assert res.status_code == 200
    assert float(res.json()["data"]["amount_fcfa"]) == pytest.approx(30000.0)


def test_edit_fuel_entry_locked_after_24h(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-008-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    # Backdate the entry
    entry = db.get(FuelEntry, entry_id)
    entry.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()

    res = client.patch(f"/api/v1/fuel/{entry_id}", json={"amount_fcfa": "30000.00"}, headers=driver_headers)
    assert res.status_code == 403


def test_edit_rejects_bad_odometer(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-012-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    # Try to set odometer equal to initial_mileage (10000) — should fail
    res = client.patch(f"/api/v1/fuel/{entry_id}", json={"odometer_km": 10000}, headers=driver_headers)
    assert res.status_code == 422


# ── US-013: Delete a fuel entry (within 24h) ─────────────────────────────────

def test_delete_fuel_entry_success(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-009-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    res = client.delete(f"/api/v1/fuel/{entry_id}", headers=driver_headers)
    assert res.status_code == 200
    assert db.get(FuelEntry, entry_id) is None


def test_delete_fuel_entry_locked_after_24h(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-013-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    entry = db.get(FuelEntry, entry_id)
    entry.created_at = datetime.now(timezone.utc) - timedelta(hours=25)
    db.commit()

    res = client.delete(f"/api/v1/fuel/{entry_id}", headers=driver_headers)
    assert res.status_code == 403


# ── US-014: Owner views fleet fuel entries ───────────────────────────────────

def test_owner_views_fleet_entries(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-014-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)

    res = client.get("/api/v1/owner/fuel-entries", headers=owner_headers)
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) >= 1
    assert data[0]["vehicle_id"] == vehicle_id


def test_owner_cannot_see_other_owners_entries(client, db, owner_headers, driver_token, driver_headers):
    """A second owner registers, their fleet is empty."""
    _seed_plans = lambda: None  # already seeded in fixture
    owner2_token = _register_and_verify(client, db, "owner2@fuel.ci", "OWNER")
    owner2_headers = {"Authorization": f"Bearer {owner2_token}"}

    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-015-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)
    client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)

    res = client.get("/api/v1/owner/fuel-entries", headers=owner2_headers)
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_owner_fleet_entries_read_only(client, db, owner_headers, driver_token, driver_headers):
    """Owner has no PATCH/DELETE on fuel entries."""
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-016-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    # These require DRIVER role — owners get 403
    assert client.patch(f"/api/v1/fuel/{entry_id}", json={"amount_fcfa": "1.00"}, headers=owner_headers).status_code == 403
    assert client.delete(f"/api/v1/fuel/{entry_id}", headers=owner_headers).status_code == 403


# ── US-024: Automatic activity logging ───────────────────────────────────────

def test_create_log_on_submit(client, db, owner_headers, driver_token, driver_headers):
    from app.models.activity_log import ActivityLog
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-017-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)

    logs = db.query(ActivityLog).filter(ActivityLog.action == "CREATE").all()
    assert len(logs) >= 1
    assert logs[-1].data_before is None
    assert logs[-1].data_after is not None


def test_update_log_on_edit(client, db, owner_headers, driver_token, driver_headers):
    from app.models.activity_log import ActivityLog
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-018-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    client.patch(f"/api/v1/fuel/{entry_id}", json={"amount_fcfa": "35000.00"}, headers=driver_headers)

    logs = db.query(ActivityLog).filter(ActivityLog.action == "UPDATE").all()
    assert len(logs) >= 1
    log = logs[-1]
    assert log.data_before is not None
    assert log.data_after is not None
    assert log.data_before["amount_fcfa"] != log.data_after["amount_fcfa"]


def test_delete_log_on_delete(client, db, owner_headers, driver_token, driver_headers):
    from app.models.activity_log import ActivityLog
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-019-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    create_res = client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    entry_id = create_res.json()["data"]["id"]

    client.delete(f"/api/v1/fuel/{entry_id}", headers=driver_headers)

    logs = db.query(ActivityLog).filter(ActivityLog.action == "DELETE").all()
    assert len(logs) >= 1
    log = logs[-1]
    assert log.data_before is not None
    assert log.fuel_entry_id is None  # entry was deleted


def test_owner_views_activity_log(client, db, owner_headers, driver_token, driver_headers):
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-020-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)

    res = client.get("/api/v1/owner/activity-logs", headers=owner_headers)
    assert res.status_code == 200
    logs = res.json()["data"]
    assert len(logs) >= 1
    assert logs[0]["action"] == "CREATE"


def test_activity_log_ordered_newest_first(client, db, owner_headers, driver_token, driver_headers):
    from app.models.activity_log import ActivityLog
    veh = _create_vehicle(client, owner_headers, {"license_plate": "FU-021-CI"})
    vehicle_id = veh.json()["data"]["id"]
    _setup_active_driver(client, db, owner_headers, driver_token, driver_headers, vehicle_id)

    # Two entries to generate two logs
    client.post("/api/v1/fuel", json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id}, headers=driver_headers)
    client.post("/api/v1/driver/deactivate", headers=driver_headers)
    client.post("/api/v1/driver/activate", json={"vehicle_id": vehicle_id}, headers=driver_headers)
    client.post(
        "/api/v1/fuel",
        json={**FUEL_PAYLOAD, "vehicle_id": vehicle_id, "odometer_km": 11000},
        headers=driver_headers,
    )

    res = client.get("/api/v1/owner/activity-logs", headers=owner_headers)
    logs = res.json()["data"]
    assert len(logs) >= 2
    # newest first: second created_at >= first
    assert logs[0]["created_at"] >= logs[1]["created_at"]
