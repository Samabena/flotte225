"""
Tests for Sprint 9 — Driver Access Control
  US-047  Owner creates & manages driver credentials
  US-048  Driver logs in with username (no email required)
  US-049  Owner-scoped driver list isolation
"""

from unittest.mock import patch

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


def _register_owner(client, db, email):
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


def _get_id(token):
    from app.core.security import decode_access_token

    return int(decode_access_token(token)["sub"])


# ── US-047: Owner creates driver credentials ──────────────────────────────────


class TestCreateDriver:
    def test_owner_can_create_driver(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47a@test.ci")
        res = client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Konan Yao",
                "username": "konan.yao",
                "password": "secret123",
            },
            headers=_headers(owner_token),
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["username"] == "konan.yao"
        assert data["is_disabled"] is False

    def test_driver_cannot_self_register(self, client, db):
        """Public /auth/register always creates OWNER — no DRIVER self-registration."""
        with patch("app.services.auth_service.send_otp_email", return_value=True):
            res = client.post(
                "/api/v1/auth/register",
                json={
                    "full_name": "Self Driver",
                    "email": "selfdrv@test.ci",
                    "password": "Password1",
                },
            )
        assert res.status_code == 201
        # The role must always be OWNER from the public endpoint
        from app.models.user import User

        user = db.query(User).filter(User.email == "selfdrv@test.ci").first()
        assert user.role == "OWNER"

    def test_duplicate_username_returns_409(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47b@test.ci")
        payload = {"full_name": "Test", "username": "dupuser", "password": "secret123"}
        client.post("/api/v1/drivers", json=payload, headers=_headers(owner_token))
        res = client.post(
            "/api/v1/drivers", json=payload, headers=_headers(owner_token)
        )
        assert res.status_code == 409

    def test_username_with_at_returns_422(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47c@test.ci")
        res = client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Bad Username",
                "username": "bad@user",
                "password": "secret123",
            },
            headers=_headers(owner_token),
        )
        assert res.status_code == 422

    def test_short_password_returns_422(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47d@test.ci")
        res = client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Short Pass",
                "username": "shortpass",
                "password": "abc",
            },
            headers=_headers(owner_token),
        )
        assert res.status_code == 422

    def test_driver_cannot_create_driver(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47e@test.ci")
        # Create a driver via owner
        client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Driver A",
                "username": "drvr47e",
                "password": "secret123",
            },
            headers=_headers(owner_token),
        )
        driver_token_res = client.post(
            "/api/v1/auth/login",
            json={"identifier": "drvr47e", "password": "secret123"},
        )
        driver_token = driver_token_res.json()["access_token"]
        # Driver trying to create another driver
        res = client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Driver B",
                "username": "drvr47e_b",
                "password": "secret123",
            },
            headers=_headers(driver_token),
        )
        assert res.status_code == 403


# ── US-047: Disable / reset password / delete ────────────────────────────────


class TestManageDriver:
    def _create_driver(self, client, db, owner_token, username):
        res = client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Test Driver",
                "username": username,
                "password": "secret123",
            },
            headers=_headers(owner_token),
        )
        return res.json()["data"]["id"]

    def test_owner_can_disable_driver(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47f@test.ci")
        driver_id = self._create_driver(client, db, owner_token, "drvr47f")

        res = client.patch(
            f"/api/v1/drivers/{driver_id}/status",
            json={"is_disabled": True},
            headers=_headers(owner_token),
        )
        assert res.status_code == 200
        assert res.json()["data"]["is_disabled"] is True

    def test_disabled_driver_cannot_login(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47g@test.ci")
        driver_id = self._create_driver(client, db, owner_token, "drvr47g")
        client.patch(
            f"/api/v1/drivers/{driver_id}/status",
            json={"is_disabled": True},
            headers=_headers(owner_token),
        )

        res = client.post(
            "/api/v1/auth/login",
            json={"identifier": "drvr47g", "password": "secret123"},
        )
        assert res.status_code == 403

    def test_owner_can_re_enable_driver(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47h@test.ci")
        driver_id = self._create_driver(client, db, owner_token, "drvr47h")
        client.patch(
            f"/api/v1/drivers/{driver_id}/status",
            json={"is_disabled": True},
            headers=_headers(owner_token),
        )
        res = client.patch(
            f"/api/v1/drivers/{driver_id}/status",
            json={"is_disabled": False},
            headers=_headers(owner_token),
        )
        assert res.json()["data"]["is_disabled"] is False
        # Should be able to log in again
        login = client.post(
            "/api/v1/auth/login",
            json={"identifier": "drvr47h", "password": "secret123"},
        )
        assert login.status_code == 200

    def test_owner_can_reset_driver_password(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47i@test.ci")
        driver_id = self._create_driver(client, db, owner_token, "drvr47i")

        res = client.patch(
            f"/api/v1/drivers/{driver_id}/password",
            json={"new_password": "newsecret99"},
            headers=_headers(owner_token),
        )
        assert res.status_code == 200
        login = client.post(
            "/api/v1/auth/login",
            json={"identifier": "drvr47i", "password": "newsecret99"},
        )
        assert login.status_code == 200

    def test_owner_can_delete_driver(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner47j@test.ci")
        driver_id = self._create_driver(client, db, owner_token, "drvr47j")

        res = client.delete(
            f"/api/v1/drivers/{driver_id}", headers=_headers(owner_token)
        )
        assert res.status_code == 204

        # Driver no longer appears in list
        list_res = client.get("/api/v1/drivers", headers=_headers(owner_token))
        ids = [d["id"] for d in list_res.json()]
        assert driver_id not in ids

    def test_manage_other_owner_driver_returns_404(self, client, db):
        _seed_plans(db)
        owner_a_token = _register_owner(client, db, "ownerA47@test.ci")
        owner_b_token = _register_owner(client, db, "ownerB47@test.ci")
        driver_id = self._create_driver(client, db, owner_a_token, "drvr47k")

        # Owner B tries to disable Owner A's driver
        res = client.patch(
            f"/api/v1/drivers/{driver_id}/status",
            json={"is_disabled": True},
            headers=_headers(owner_b_token),
        )
        assert res.status_code == 404


# ── US-048: Driver login with username ────────────────────────────────────────


class TestDriverLogin:
    def test_driver_logs_in_with_username(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner48a@test.ci")
        client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Login Driver",
                "username": "logindrv48",
                "password": "mypassword",
            },
            headers=_headers(owner_token),
        )

        res = client.post(
            "/api/v1/auth/login",
            json={"identifier": "logindrv48", "password": "mypassword"},
        )
        assert res.status_code == 200
        assert "access_token" in res.json()
        assert res.json()["role"] == "DRIVER"

    def test_driver_login_wrong_password(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner48b@test.ci")
        client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Bad Pass",
                "username": "badpass48",
                "password": "correct",
            },
            headers=_headers(owner_token),
        )

        res = client.post(
            "/api/v1/auth/login", json={"identifier": "badpass48", "password": "wrong"}
        )
        assert res.status_code == 401

    def test_owner_still_logs_in_with_email(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner48c@test.ci")
        assert owner_token is not None
        # Re-login with email as identifier
        res = client.post(
            "/api/v1/auth/login",
            json={"identifier": "owner48c@test.ci", "password": "Password1"},
        )
        assert res.status_code == 200
        assert res.json()["role"] == "OWNER"


# ── US-049: Owner-scoped driver list isolation ────────────────────────────────


class TestDriverIsolation:
    def test_owner_only_sees_own_drivers(self, client, db):
        _seed_plans(db)
        owner_a = _register_owner(client, db, "ownerA49@test.ci")
        owner_b = _register_owner(client, db, "ownerB49@test.ci")

        client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Driver of A",
                "username": "drvr49a",
                "password": "secret123",
            },
            headers=_headers(owner_a),
        )
        client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Driver of B",
                "username": "drvr49b",
                "password": "secret123",
            },
            headers=_headers(owner_b),
        )

        res_a = client.get("/api/v1/drivers", headers=_headers(owner_a))
        res_b = client.get("/api/v1/drivers", headers=_headers(owner_b))

        usernames_a = [d["username"] for d in res_a.json()]
        usernames_b = [d["username"] for d in res_b.json()]

        assert "drvr49a" in usernames_a
        assert "drvr49b" not in usernames_a

        assert "drvr49b" in usernames_b
        assert "drvr49a" not in usernames_b

    def test_driver_cannot_list_drivers(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner49d@test.ci")
        client.post(
            "/api/v1/drivers",
            json={
                "full_name": "Driver D",
                "username": "drvr49d",
                "password": "secret123",
            },
            headers=_headers(owner_token),
        )
        driver_token = client.post(
            "/api/v1/auth/login",
            json={"identifier": "drvr49d", "password": "secret123"},
        ).json()["access_token"]

        res = client.get("/api/v1/drivers", headers=_headers(driver_token))
        assert res.status_code == 403

    def test_list_drivers_empty_for_new_owner(self, client, db):
        _seed_plans(db)
        owner_token = _register_owner(client, db, "owner49e@test.ci")
        res = client.get("/api/v1/drivers", headers=_headers(owner_token))
        assert res.status_code == 200
        assert res.json() == []
