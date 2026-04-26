"""
Tests for Sprint 2 vehicle management stories:
  US-005 — Register a vehicle
  US-006 — Edit a vehicle
  US-007 — Pause and resume a vehicle
  US-008 — Archive a vehicle (soft delete)
  US-009 — Assign/remove drivers from a vehicle
  US-022 — Driver views assigned vehicles
  US-023 — Toggle driving status
"""

import pytest
from unittest.mock import patch

from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan


# ── Fixtures & helpers ────────────────────────────────────────────────────────

VEHICLE_PAYLOAD = {
    "name": "Camion Alpha",
    "brand": "Toyota",
    "model": "HiLux",
    "year": 2020,
    "license_plate": "AB-001-CI",
    "fuel_type": "Diesel",
    "initial_mileage": 15000,
}


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


def _register_and_verify(client, db, email, role="OWNER"):
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


def _create_driver_in_db(db, owner_id, username="testdriver.veh"):
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


@pytest.fixture()
def owner_token(client, db):
    _seed_plans(db)
    return _register_and_verify(client, db, "owner@veh.ci")


@pytest.fixture()
def driver_token(client, db, owner_token):
    from app.core.security import decode_access_token

    owner_id = int(decode_access_token(owner_token)["sub"])
    _create_driver_in_db(db, owner_id, username="testdriver.veh")
    res = client.post(
        "/api/v1/auth/login",
        json={"identifier": "testdriver.veh", "password": "Password1"},
    )
    return res.json()["access_token"]


@pytest.fixture()
def owner_headers(owner_token):
    return {"Authorization": f"Bearer {owner_token}"}


@pytest.fixture()
def driver_headers(driver_token):
    return {"Authorization": f"Bearer {driver_token}"}


def _create_vehicle(client, owner_headers, payload=None):
    p = {**VEHICLE_PAYLOAD, **(payload or {})}
    return client.post("/api/v1/vehicles", json=p, headers=owner_headers)


# ── US-005: Register a vehicle ────────────────────────────────────────────────


def test_create_vehicle_success(client, owner_headers):
    res = _create_vehicle(client, owner_headers)
    assert res.status_code == 201
    data = res.json()["data"]
    assert data["name"] == "Camion Alpha"
    assert data["status"] == "active"
    assert data["license_plate"] == "AB-001-CI"


def test_create_vehicle_duplicate_plate(client, owner_headers):
    _create_vehicle(client, owner_headers)
    res = _create_vehicle(client, owner_headers)
    assert res.status_code == 409


def test_create_vehicle_missing_required_field(client, owner_headers):
    payload = {**VEHICLE_PAYLOAD}
    del payload["license_plate"]
    res = client.post("/api/v1/vehicles", json=payload, headers=owner_headers)
    assert res.status_code == 422


@pytest.mark.skip(reason="Subscription tiering deferred — plan gating disabled")
def test_create_vehicle_plan_limit(client, db, owner_headers):
    """Starter plan allows max 2 vehicles — 3rd should be rejected."""
    _create_vehicle(client, owner_headers, {"license_plate": "AA-001-CI"})
    _create_vehicle(client, owner_headers, {"license_plate": "AA-002-CI"})
    res = _create_vehicle(client, owner_headers, {"license_plate": "AA-003-CI"})
    assert res.status_code == 403


def test_create_vehicle_requires_owner_role(client, driver_headers):
    res = _create_vehicle(client, driver_headers)
    assert res.status_code == 403


# ── US-006: Edit a vehicle ────────────────────────────────────────────────────


def test_update_vehicle_success(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    res = client.patch(
        f"/api/v1/vehicles/{v_id}", json={"name": "Nouveau Nom"}, headers=owner_headers
    )
    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Nouveau Nom"


def test_update_vehicle_duplicate_plate(client, owner_headers):
    _create_vehicle(client, owner_headers, {"license_plate": "XX-001-CI"})
    v2 = _create_vehicle(client, owner_headers, {"license_plate": "XX-002-CI"}).json()[
        "data"
    ]
    res = client.patch(
        f"/api/v1/vehicles/{v2['id']}",
        json={"license_plate": "XX-001-CI"},
        headers=owner_headers,
    )
    assert res.status_code == 409


def test_update_vehicle_not_found(client, owner_headers):
    res = client.patch(
        "/api/v1/vehicles/9999", json={"name": "X"}, headers=owner_headers
    )
    assert res.status_code == 404


# ── US-007: Pause and resume ──────────────────────────────────────────────────


def test_pause_and_resume_vehicle(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]

    pause_res = client.post(f"/api/v1/vehicles/{v_id}/pause", headers=owner_headers)
    assert pause_res.status_code == 200
    assert pause_res.json()["data"]["status"] == "paused"

    resume_res = client.post(f"/api/v1/vehicles/{v_id}/resume", headers=owner_headers)
    assert resume_res.status_code == 200
    assert resume_res.json()["data"]["status"] == "active"


def test_pause_already_paused(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    client.post(f"/api/v1/vehicles/{v_id}/pause", headers=owner_headers)
    res = client.post(f"/api/v1/vehicles/{v_id}/pause", headers=owner_headers)
    assert res.status_code == 400


def test_resume_active_vehicle_fails(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    res = client.post(f"/api/v1/vehicles/{v_id}/resume", headers=owner_headers)
    assert res.status_code == 400


# ── US-008: Archive / restore ─────────────────────────────────────────────────


def test_archive_vehicle(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    res = client.post(f"/api/v1/vehicles/{v_id}/archive", headers=owner_headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "archived"
    assert res.json()["data"]["archived_at"] is not None


def test_archived_vehicle_not_in_active_list(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    client.post(f"/api/v1/vehicles/{v_id}/archive", headers=owner_headers)

    list_res = client.get("/api/v1/vehicles", headers=owner_headers)
    ids = [v["id"] for v in list_res.json()["data"]]
    assert v_id not in ids


def test_archived_vehicle_in_archived_list(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    client.post(f"/api/v1/vehicles/{v_id}/archive", headers=owner_headers)

    arch_res = client.get("/api/v1/vehicles/archived", headers=owner_headers)
    ids = [v["id"] for v in arch_res.json()["data"]]
    assert v_id in ids


def test_restore_archived_vehicle(client, owner_headers):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    client.post(f"/api/v1/vehicles/{v_id}/archive", headers=owner_headers)
    res = client.post(f"/api/v1/vehicles/{v_id}/restore", headers=owner_headers)
    assert res.status_code == 200
    assert res.json()["data"]["status"] == "active"


def test_archive_resets_active_driver(client, db, owner_headers, driver_headers):
    """Archiving a vehicle resets the driving status of any active driver."""
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]

    # Get driver's id from DB
    driver = db.query(User).filter(User.username == "testdriver.veh").first()

    # Assign driver to vehicle
    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )

    # Activate driver
    client.post(
        "/api/v1/driver/activate", json={"vehicle_id": v_id}, headers=driver_headers
    )

    # Verify driver is active
    db.expire(driver)
    assert driver.driving_status is True

    # Archive vehicle
    client.post(f"/api/v1/vehicles/{v_id}/archive", headers=owner_headers)

    # Driver should now be inactive
    db.expire(driver)
    assert driver.driving_status is False
    assert driver.active_vehicle_id is None


# ── US-009: Assign / remove drivers ──────────────────────────────────────────


def test_assign_driver_to_vehicle(client, db, owner_headers, driver_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()

    res = client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    assert res.status_code == 201

    list_res = client.get(f"/api/v1/vehicles/{v_id}/drivers", headers=owner_headers)
    ids = [d["id"] for d in list_res.json()["data"]]
    assert driver.id in ids


def test_assign_driver_duplicate(client, db, owner_headers, driver_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()

    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    res = client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    assert res.status_code == 409


def test_cannot_assign_owner_as_driver(client, db, owner_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    owner = db.query(User).filter(User.email == "owner@veh.ci").first()

    res = client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": owner.id},
        headers=owner_headers,
    )
    assert res.status_code == 400


def test_remove_driver_from_vehicle(client, db, owner_headers, driver_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()

    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    res = client.delete(
        f"/api/v1/vehicles/{v_id}/drivers/{driver.id}", headers=owner_headers
    )
    assert res.status_code == 200

    list_res = client.get(f"/api/v1/vehicles/{v_id}/drivers", headers=owner_headers)
    assert list_res.json()["data"] == []


def test_remove_driver_resets_driving_status(client, db, owner_headers, driver_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()

    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    client.post(
        "/api/v1/driver/activate", json={"vehicle_id": v_id}, headers=driver_headers
    )

    db.expire(driver)
    assert driver.driving_status is True

    client.delete(f"/api/v1/vehicles/{v_id}/drivers/{driver.id}", headers=owner_headers)

    db.expire(driver)
    assert driver.driving_status is False


# ── US-022: Driver views assigned vehicles ────────────────────────────────────


def test_driver_sees_assigned_vehicles(client, db, owner_headers, driver_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()
    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )

    res = client.get("/api/v1/driver/vehicles", headers=driver_headers)
    assert res.status_code == 200
    ids = [v["id"] for v in res.json()["data"]]
    assert v_id in ids


def test_driver_sees_empty_list_when_unassigned(client, driver_headers):
    res = client.get("/api/v1/driver/vehicles", headers=driver_headers)
    assert res.status_code == 200
    assert res.json()["data"] == []


def test_driver_does_not_see_archived_vehicle(
    client, db, owner_headers, driver_headers
):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()
    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    client.post(f"/api/v1/vehicles/{v_id}/archive", headers=owner_headers)

    res = client.get("/api/v1/driver/vehicles", headers=driver_headers)
    ids = [v["id"] for v in res.json()["data"]]
    assert v_id not in ids


# ── US-023: Toggle driving status ─────────────────────────────────────────────


def test_driver_activates_and_deactivates(client, db, owner_headers, driver_headers):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()
    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )

    activate_res = client.post(
        "/api/v1/driver/activate", json={"vehicle_id": v_id}, headers=driver_headers
    )
    assert activate_res.status_code == 200
    assert activate_res.json()["data"]["driving_status"] is True

    deactivate_res = client.post("/api/v1/driver/deactivate", headers=driver_headers)
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["data"]["driving_status"] is False


def test_driver_cannot_activate_unassigned_vehicle(
    client, owner_headers, driver_headers
):
    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    # No assignment — should be rejected
    res = client.post(
        "/api/v1/driver/activate", json={"vehicle_id": v_id}, headers=driver_headers
    )
    assert res.status_code == 403


def test_driver_cannot_activate_paused_vehicle(
    client, db, owner_headers, driver_headers
):
    from app.models.user import User

    v_id = _create_vehicle(client, owner_headers).json()["data"]["id"]
    driver = db.query(User).filter(User.username == "testdriver.veh").first()
    client.post(
        f"/api/v1/vehicles/{v_id}/drivers",
        json={"driver_id": driver.id},
        headers=owner_headers,
    )
    client.post(f"/api/v1/vehicles/{v_id}/pause", headers=owner_headers)

    res = client.post(
        "/api/v1/driver/activate", json={"vehicle_id": v_id}, headers=driver_headers
    )
    assert res.status_code == 400


def test_owner_cannot_use_driver_endpoints(client, owner_headers):
    res = client.get("/api/v1/driver/vehicles", headers=owner_headers)
    assert res.status_code == 403
