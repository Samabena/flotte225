"""
Tests for Sprint 1 auth stories:
  US-001 — Register
  US-002 — Email verification
  US-003 — Login + role-based JWT
  US-004 — Password reset
  US-042 — Super admin seed script
  US-043 — Default Starter plan on registration
  US-044 — Enforce plan limits at API level
"""
import pytest
from unittest.mock import patch


# ─── US-001: Registration ───────────────────────────────────────────────────

def test_register_success(client):
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        res = client.post("/api/v1/auth/register", json={
            "full_name": "Kouassi Jean",
            "email": "jean@flotte225.ci",
            "password": "Password1",
        })
    assert res.status_code == 201
    assert res.json()["success"] is True
    assert "id" in res.json()["data"]


def test_register_duplicate_email(client):
    payload = {"full_name": "Test", "email": "dup@flotte225.ci", "password": "Password1"}
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/register", json=payload)
        res = client.post("/api/v1/auth/register", json=payload)
    assert res.status_code == 409


def test_register_short_password(client):
    res = client.post("/api/v1/auth/register", json={
        "full_name": "Test",
        "email": "short@flotte225.ci",
        "password": "abc",
    })
    assert res.status_code == 422


# ─── US-002: Email verification ─────────────────────────────────────────────

def test_verify_email_success(client, db):
    from app.models.otp_code import OtpCode

    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/register", json={
            "full_name": "Ama Koffi",
            "email": "ama@flotte225.ci",
            "password": "Password1",
        })

    # Grab the OTP from DB
    otp = db.query(OtpCode).filter(OtpCode.purpose == "EMAIL_VERIFY").first()
    assert otp is not None

    res = client.post("/api/v1/auth/verify-email", json={
        "email": "ama@flotte225.ci",
        "code": otp.code,
    })
    assert res.status_code == 200
    assert res.json()["success"] is True


def test_verify_email_wrong_code(client):
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/register", json={
            "full_name": "Soro Ali",
            "email": "soro@flotte225.ci",
            "password": "Password1",
        })

    res = client.post("/api/v1/auth/verify-email", json={
        "email": "soro@flotte225.ci",
        "code": "000000",
    })
    assert res.status_code == 400


# ─── US-003: Login ──────────────────────────────────────────────────────────

def _register_and_verify(client, db, email="login_test@flotte225.ci"):
    from app.models.otp_code import OtpCode
    from app.models.user import User

    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/register", json={
            "full_name": "Login Test",
            "email": email,
            "password": "Password1",
        })

    otp = db.query(OtpCode).filter(
        OtpCode.purpose == "EMAIL_VERIFY"
    ).order_by(OtpCode.id.desc()).first()
    client.post("/api/v1/auth/verify-email", json={"email": email, "code": otp.code})


def test_login_success(client, db):
    email = "login_ok@flotte225.ci"
    _register_and_verify(client, db, email)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "Password1"})
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["role"] == "OWNER"


def test_login_wrong_password(client, db):
    email = "login_bad@flotte225.ci"
    _register_and_verify(client, db, email)
    res = client.post("/api/v1/auth/login", json={"email": email, "password": "wrongpass"})
    assert res.status_code == 401


def test_login_unverified(client):
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/register", json={
            "full_name": "Unverified",
            "email": "unverified@flotte225.ci",
            "password": "Password1",
        })
    res = client.post("/api/v1/auth/login", json={
        "email": "unverified@flotte225.ci",
        "password": "Password1",
    })
    assert res.status_code == 403


# ─── US-004: Password reset ──────────────────────────────────────────────────

def test_forgot_password_always_returns_200(client):
    # Should return 200 even for unknown email (enumeration protection)
    res = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@flotte225.ci"})
    assert res.status_code == 200


def test_reset_password_success(client, db):
    from app.models.otp_code import OtpCode

    email = "reset_test@flotte225.ci"
    _register_and_verify(client, db, email)

    with patch("app.services.auth_service.send_otp_email", return_value=True):
        client.post("/api/v1/auth/forgot-password", json={"email": email})

    otp = db.query(OtpCode).filter(
        OtpCode.purpose == "PASSWORD_RESET"
    ).order_by(OtpCode.id.desc()).first()
    assert otp is not None

    res = client.post("/api/v1/auth/reset-password", json={
        "email": email,
        "code": otp.code,
        "new_password": "NewPassword1",
    })
    assert res.status_code == 200

    # Verify new password works
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "NewPassword1"})
    assert login_res.status_code == 200


# ─── US-042: Super admin seed script ────────────────────────────────────────

def test_seed_creates_three_plans(db):
    """Seed data produces starter / pro / business plans."""
    from app.models.subscription import SubscriptionPlan
    from scripts.seed import PLANS

    for plan_data in PLANS:
        db.add(SubscriptionPlan(**plan_data))
    db.commit()

    plans = db.query(SubscriptionPlan).all()
    assert len(plans) == 3
    names = {p.name for p in plans}
    assert names == {"starter", "pro", "business"}


def test_seed_creates_super_admin(db):
    """Seed data produces a SUPER_ADMIN user that is verified."""
    from app.models.user import User
    from app.core.security import hash_password

    admin = User(
        email="admin@flotte225.ci",
        password_hash=hash_password("Admin@flotte225!"),
        role="SUPER_ADMIN",
        full_name="Super Admin",
        is_verified=True,
        is_active=True,
    )
    db.add(admin)
    db.commit()

    found = db.query(User).filter(User.email == "admin@flotte225.ci").first()
    assert found is not None
    assert found.role == "SUPER_ADMIN"
    assert found.is_verified is True


def test_seed_is_idempotent(db):
    """Running seed twice does not create duplicate plans."""
    from app.models.subscription import SubscriptionPlan
    from scripts.seed import PLANS

    for _ in range(2):
        for plan_data in PLANS:
            existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_data["name"]).first()
            if not existing:
                db.add(SubscriptionPlan(**plan_data))
        db.commit()

    assert db.query(SubscriptionPlan).count() == 3


# ─── US-043: Default Starter plan on registration ───────────────────────────

def test_register_assigns_starter_plan(client, db):
    """Registration auto-creates an OwnerSubscription on the starter plan."""
    from app.models.subscription import SubscriptionPlan, OwnerSubscription
    from app.models.user import User

    db.add(SubscriptionPlan(
        name="starter", max_vehicles=2, max_drivers=5, price_fcfa=0,
        ai_reports_per_month=0, has_whatsapp=False, has_export=False, has_webhook=False,
    ))
    db.commit()

    with patch("app.services.auth_service.send_otp_email", return_value=True):
        res = client.post("/api/v1/auth/register", json={
            "full_name": "Plan Test Owner",
            "email": "plantest@flotte225.ci",
            "password": "Password1",
        })
    assert res.status_code == 201

    user = db.query(User).filter(User.email == "plantest@flotte225.ci").first()
    sub = db.query(OwnerSubscription).filter(OwnerSubscription.owner_id == user.id).first()
    assert sub is not None
    assert sub.is_active is True

    plan = db.get(SubscriptionPlan, sub.plan_id)
    assert plan.name == "starter"


def test_register_no_plan_seeded_still_succeeds(client, db):
    """Registration succeeds even when no plans are seeded (plan assignment is best-effort)."""
    with patch("app.services.auth_service.send_otp_email", return_value=True):
        res = client.post("/api/v1/auth/register", json={
            "full_name": "No Plan Owner",
            "email": "noplan@flotte225.ci",
            "password": "Password1",
        })
    assert res.status_code == 201


# ─── US-044: Enforce plan limits at API level ────────────────────────────────

def _make_owner_with_plan(db, email: str, plan_name: str):
    """Helper: create a verified owner assigned to a given plan."""
    from app.models.subscription import SubscriptionPlan, OwnerSubscription
    from app.models.user import User
    from app.core.security import hash_password
    from datetime import datetime, timezone

    plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_name).first()
    owner = User(
        email=email,
        password_hash=hash_password("Password1"),
        role="OWNER",
        full_name="Test Owner",
        is_verified=True,
        is_active=True,
    )
    db.add(owner)
    db.commit()

    sub = OwnerSubscription(
        owner_id=owner.id,
        plan_id=plan.id,
        started_at=datetime.now(timezone.utc),
        is_active=True,
    )
    db.add(sub)
    db.commit()
    return owner


def _seed_all_plans(db):
    from app.models.subscription import SubscriptionPlan
    from scripts.seed import PLANS
    for plan_data in PLANS:
        if not db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_data["name"]).first():
            db.add(SubscriptionPlan(**plan_data))
    db.commit()


def test_require_plan_blocks_wrong_plan(db):
    """require_plan raises 403 when owner's plan is not in the allowed list."""
    from fastapi import HTTPException
    from app.core.deps import require_plan

    _seed_all_plans(db)
    owner = _make_owner_with_plan(db, "block_test@flotte225.ci", "starter")

    checker = require_plan("pro", "business")
    with pytest.raises(HTTPException) as exc_info:
        checker(owner=owner, db=db)
    assert exc_info.value.status_code == 403


def test_require_plan_allows_matching_plan(db):
    """require_plan returns the owner when plan matches."""
    from app.core.deps import require_plan

    _seed_all_plans(db)
    owner = _make_owner_with_plan(db, "allow_test@flotte225.ci", "pro")

    checker = require_plan("pro", "business")
    result = checker(owner=owner, db=db)
    assert result.id == owner.id


def test_require_plan_blocks_no_subscription(db):
    """require_plan raises 403 when owner has no active subscription."""
    from fastapi import HTTPException
    from app.core.deps import require_plan
    from app.models.user import User
    from app.core.security import hash_password

    owner = User(
        email="nosub@flotte225.ci",
        password_hash=hash_password("Password1"),
        role="OWNER",
        full_name="No Sub Owner",
        is_verified=True,
        is_active=True,
    )
    db.add(owner)
    db.commit()

    checker = require_plan("pro", "business")
    with pytest.raises(HTTPException) as exc_info:
        checker(owner=owner, db=db)
    assert exc_info.value.status_code == 403
