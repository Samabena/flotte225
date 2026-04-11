"""
Tests for Sprint 6 — Super Admin & Subscription UI
  US-036  View & search all users
  US-037  Suspend & reactivate a user
  US-038  Permanently delete a user
  US-039  View any owner's fleet (admin)
  US-040  Manage subscription plans per owner
  US-046  Owner views current plan & usage
  US-045  Upgrade prompt for locked features (403 payload)
"""
import pytest
from unittest.mock import patch

from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan, OwnerSubscription
from app.models.vehicle import Vehicle


# ── Helpers ───────────────────────────────────────────────────────────────────

def _seed_plans(db):
    from scripts.seed import PLANS
    for plan_data in PLANS:
        if not db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_data["name"]).first():
            db.add(SubscriptionPlan(**plan_data))
    db.commit()


def _register_and_verify(client, db, email, role="OWNER"):
    """Register OWNER or DRIVER via API."""
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


def _create_admin(client, db, email):
    """Create SUPER_ADMIN directly in DB (SUPER_ADMIN cannot self-register via API)."""
    from app.core.security import hash_password
    from app.models.user import User as UserModel
    admin = UserModel(
        email=email,
        password_hash=hash_password("AdminPass1"),
        role="SUPER_ADMIN",
        full_name="Test Admin",
        is_verified=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "AdminPass1"})
    return res.json()["access_token"]


def _get_user_id(token):
    from app.core.security import decode_access_token
    return int(decode_access_token(token)["sub"])


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _create_vehicle(client, owner_headers, plate="MT-001-CI"):
    return client.post("/api/v1/vehicles", json={
        "name": "Véhicule Test",
        "brand": "Toyota",
        "model": "HiLux",
        "license_plate": plate,
        "fuel_type": "Diesel",
        "initial_mileage": 10000,
    }, headers=owner_headers).json()["data"]["id"]


# ── US-036: List / search users ───────────────────────────────────────────────

class TestListUsers:
    def test_admin_lists_all_users(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin36a@test.ci")
        _register_and_verify(client, db, "owner36a@test.ci", role="OWNER")
        _register_and_verify(client, db, "driver36a@test.ci", role="DRIVER")

        res = client.get("/api/v1/admin/users", headers=_headers(admin_token))
        assert res.status_code == 200
        assert res.json()["success"] is True
        emails = [u["email"] for u in res.json()["data"]]
        assert "owner36a@test.ci" in emails
        assert "driver36a@test.ci" in emails

    def test_non_admin_cannot_list_users(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner36b@test.ci")
        res = client.get("/api/v1/admin/users", headers=_headers(owner_token))
        assert res.status_code == 403

    def test_search_by_email(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin36c@test.ci")
        _register_and_verify(client, db, "findme36@test.ci", role="OWNER")

        res = client.get("/api/v1/admin/users?q=findme36", headers=_headers(admin_token))
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["email"] == "findme36@test.ci"

    def test_filter_by_role(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin36d@test.ci")
        _register_and_verify(client, db, "owner36d@test.ci", role="OWNER")
        _register_and_verify(client, db, "driver36d@test.ci", role="DRIVER")

        res = client.get("/api/v1/admin/users?role=DRIVER", headers=_headers(admin_token))
        data = res.json()["data"]
        assert all(u["role"] == "DRIVER" for u in data)

    def test_search_no_match_returns_empty(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin36e@test.ci")

        res = client.get("/api/v1/admin/users?q=zzznomatch", headers=_headers(admin_token))
        assert res.json()["data"] == []


# ── US-037: Suspend / reactivate ──────────────────────────────────────────────

class TestSuspendReactivate:
    def test_admin_can_suspend_owner(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin37a@test.ci")
        owner_token = _register_and_verify(client, db, "owner37a@test.ci")
        owner_id = _get_user_id(owner_token)

        res = client.patch(f"/api/v1/admin/users/{owner_id}/suspend", headers=_headers(admin_token))
        assert res.status_code == 200
        assert res.json()["data"]["is_active"] is False

    def test_suspended_user_cannot_login(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin37b@test.ci")
        owner_token = _register_and_verify(client, db, "owner37b@test.ci")
        owner_id = _get_user_id(owner_token)

        client.patch(f"/api/v1/admin/users/{owner_id}/suspend", headers=_headers(admin_token))
        res = client.post("/api/v1/auth/login", json={"email": "owner37b@test.ci", "password": "Password1"})
        assert res.status_code == 403  # auth_service returns 403 for disabled accounts

    def test_admin_can_reactivate_user(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin37c@test.ci")
        owner_token = _register_and_verify(client, db, "owner37c@test.ci")
        owner_id = _get_user_id(owner_token)

        client.patch(f"/api/v1/admin/users/{owner_id}/suspend", headers=_headers(admin_token))
        res = client.patch(f"/api/v1/admin/users/{owner_id}/reactivate", headers=_headers(admin_token))
        assert res.status_code == 200
        assert res.json()["data"]["is_active"] is True

    def test_cannot_suspend_super_admin(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin37d@test.ci")
        admin2_token = _create_admin(client, db, "sadmin37e@test.ci")
        admin2_id = _get_user_id(admin2_token)

        res = client.patch(f"/api/v1/admin/users/{admin2_id}/suspend", headers=_headers(admin_token))
        assert res.status_code == 403

    def test_suspend_unknown_user_returns_404(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin37f@test.ci")
        res = client.patch("/api/v1/admin/users/99999/suspend", headers=_headers(admin_token))
        assert res.status_code == 404


# ── US-038: Permanently delete ────────────────────────────────────────────────

class TestDeleteUser:
    def test_admin_can_delete_driver(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin38a@test.ci")
        driver_token = _register_and_verify(client, db, "driver38a@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        res = client.delete(f"/api/v1/admin/users/{driver_id}", headers=_headers(admin_token))
        assert res.status_code == 204

        list_res = client.get("/api/v1/admin/users", headers=_headers(admin_token))
        ids = [u["id"] for u in list_res.json()["data"]]
        assert driver_id not in ids

    def test_admin_can_delete_owner_and_fleet(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin38b@test.ci")
        owner_token = _register_and_verify(client, db, "owner38b@test.ci")
        owner_id = _get_user_id(owner_token)
        _create_vehicle(client, _headers(owner_token), plate="DEL-001-CI")

        res = client.delete(f"/api/v1/admin/users/{owner_id}", headers=_headers(admin_token))
        assert res.status_code == 204

        assert db.query(Vehicle).filter(Vehicle.owner_id == owner_id).count() == 0

    def test_cannot_delete_super_admin(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin38c@test.ci")
        admin2_token = _create_admin(client, db, "sadmin38d@test.ci")
        admin2_id = _get_user_id(admin2_token)

        res = client.delete(f"/api/v1/admin/users/{admin2_id}", headers=_headers(admin_token))
        assert res.status_code == 403

    def test_admin_cannot_delete_self(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin38e@test.ci")
        admin_id = _get_user_id(admin_token)

        res = client.delete(f"/api/v1/admin/users/{admin_id}", headers=_headers(admin_token))
        assert res.status_code == 403

    def test_delete_unknown_user_returns_404(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin38f@test.ci")
        res = client.delete("/api/v1/admin/users/99998", headers=_headers(admin_token))
        assert res.status_code == 404


# ── US-039: View any owner's fleet ───────────────────────────────────────────

class TestAdminViewFleet:
    def test_admin_sees_owner_vehicles(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin39a@test.ci")
        owner_token = _register_and_verify(client, db, "owner39a@test.ci")
        owner_id = _get_user_id(owner_token)
        _create_vehicle(client, _headers(owner_token), plate="FLT-001-CI")

        res = client.get(f"/api/v1/admin/users/{owner_id}/fleet", headers=_headers(admin_token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["owner_id"] == owner_id
        assert len(data["vehicles"]) == 1
        assert data["vehicles"][0]["license_plate"] == "FLT-001-CI"

    def test_fleet_empty_for_owner_with_no_vehicles(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin39b@test.ci")
        owner_token = _register_and_verify(client, db, "owner39b@test.ci")
        owner_id = _get_user_id(owner_token)

        res = client.get(f"/api/v1/admin/users/{owner_id}/fleet", headers=_headers(admin_token))
        assert res.status_code == 200
        assert res.json()["data"]["vehicles"] == []

    def test_fleet_returns_400_for_non_owner(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin39c@test.ci")
        driver_token = _register_and_verify(client, db, "driver39c@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        res = client.get(f"/api/v1/admin/users/{driver_id}/fleet", headers=_headers(admin_token))
        assert res.status_code == 400

    def test_non_admin_cannot_view_fleet(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner39d@test.ci")
        owner_id = _get_user_id(owner_token)

        res = client.get(f"/api/v1/admin/users/{owner_id}/fleet", headers=_headers(owner_token))
        assert res.status_code == 403


# ── US-040: Assign plan to owner ──────────────────────────────────────────────

class TestAssignPlan:
    def test_admin_can_upgrade_owner_to_pro(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin40a@test.ci")
        owner_token = _register_and_verify(client, db, "owner40a@test.ci")
        owner_id = _get_user_id(owner_token)

        res = client.put(
            f"/api/v1/admin/users/{owner_id}/plan",
            json={"plan_name": "pro"},
            headers=_headers(admin_token),
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

        plan_res = client.get("/api/v1/subscription/my-plan", headers=_headers(owner_token))
        assert plan_res.json()["data"]["plan"]["name"] == "pro"

    def test_admin_can_downgrade_to_starter(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin40b@test.ci")
        owner_token = _register_and_verify(client, db, "owner40b@test.ci")
        owner_id = _get_user_id(owner_token)

        client.put(
            f"/api/v1/admin/users/{owner_id}/plan",
            json={"plan_name": "pro"},
            headers=_headers(admin_token),
        )
        res = client.put(
            f"/api/v1/admin/users/{owner_id}/plan",
            json={"plan_name": "starter"},
            headers=_headers(admin_token),
        )
        assert res.status_code == 200

        plan_res = client.get("/api/v1/subscription/my-plan", headers=_headers(owner_token))
        assert plan_res.json()["data"]["plan"]["name"] == "starter"

    def test_invalid_plan_name_returns_400(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin40c@test.ci")
        owner_token = _register_and_verify(client, db, "owner40c@test.ci")
        owner_id = _get_user_id(owner_token)

        res = client.put(
            f"/api/v1/admin/users/{owner_id}/plan",
            json={"plan_name": "gold"},
            headers=_headers(admin_token),
        )
        assert res.status_code == 400

    def test_assign_plan_to_non_owner_returns_400(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin40d@test.ci")
        driver_token = _register_and_verify(client, db, "driver40d@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        res = client.put(
            f"/api/v1/admin/users/{driver_id}/plan",
            json={"plan_name": "pro"},
            headers=_headers(admin_token),
        )
        assert res.status_code == 400

    def test_non_admin_cannot_assign_plan(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner40e@test.ci")
        owner_id = _get_user_id(owner_token)

        res = client.put(
            f"/api/v1/admin/users/{owner_id}/plan",
            json={"plan_name": "pro"},
            headers=_headers(owner_token),
        )
        assert res.status_code == 403


# ── US-046: Owner views plan & usage ─────────────────────────────────────────

class TestMyPlan:
    def test_owner_sees_starter_plan_on_registration(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner46a@test.ci")
        res = client.get("/api/v1/subscription/my-plan", headers=_headers(owner_token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["plan"]["name"] == "starter"
        assert data["active_vehicles"] == 0
        assert data["active_drivers"] == 0

    def test_usage_counts_active_vehicles(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner46b@test.ci")
        _create_vehicle(client, _headers(owner_token), plate="PLN-001-CI")
        _create_vehicle(client, _headers(owner_token), plate="PLN-002-CI")

        res = client.get("/api/v1/subscription/my-plan", headers=_headers(owner_token))
        assert res.json()["data"]["active_vehicles"] == 2

    def test_usage_counts_assigned_drivers(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner46c@test.ci")
        driver_token = _register_and_verify(client, db, "driver46c@test.ci", role="DRIVER")
        driver_id = _get_user_id(driver_token)

        v1 = _create_vehicle(client, _headers(owner_token), plate="PLN-003-CI")
        client.post(f"/api/v1/vehicles/{v1}/drivers", json={"driver_id": driver_id}, headers=_headers(owner_token))

        res = client.get("/api/v1/subscription/my-plan", headers=_headers(owner_token))
        assert res.json()["data"]["active_drivers"] == 1

    def test_driver_cannot_access_plan_endpoint(self, client, db):
        _seed_plans(db)
        driver_token = _register_and_verify(client, db, "driver46d@test.ci", role="DRIVER")
        res = client.get("/api/v1/subscription/my-plan", headers=_headers(driver_token))
        assert res.status_code == 403

    def test_plan_shows_feature_flags(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin46a@test.ci")
        owner_token = _register_and_verify(client, db, "owner46e@test.ci")
        owner_id = _get_user_id(owner_token)

        client.put(
            f"/api/v1/admin/users/{owner_id}/plan",
            json={"plan_name": "business"},
            headers=_headers(admin_token),
        )
        res = client.get("/api/v1/subscription/my-plan", headers=_headers(owner_token))
        plan = res.json()["data"]["plan"]
        assert plan["name"] == "business"
        assert plan["has_export"] is True
        assert plan["has_whatsapp"] is True


# ── US-045: Upgrade prompt — 403 payload contains plan context ───────────────

class TestUpgradePrompt:
    """US-045 — When a starter owner hits the vehicle limit, the API returns
    403 with a message the frontend uses to show an upgrade prompt."""

    def test_starter_owner_blocked_after_vehicle_limit(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner45a@test.ci")

        # Starter plan has max_vehicles = 2
        for i in range(2):
            _create_vehicle(client, _headers(owner_token), plate=f"LIM-{i:03d}-CI")

        # 3rd vehicle should be blocked
        res = client.post("/api/v1/vehicles", json={
            "name": "Extra",
            "brand": "Ford",
            "model": "Ranger",
            "license_plate": "LIM-099-CI",
            "fuel_type": "Diesel",
            "initial_mileage": 5000,
        }, headers=_headers(owner_token))
        assert res.status_code == 403
        assert "limit" in res.json()["detail"].lower() or "plan" in res.json()["detail"].lower()
