"""
Tests for Sprint 7 — Export, WhatsApp & Admin Analytics
  US-031  Export fleet data (PDF / Excel)
  US-034  Configure WhatsApp notifications
  US-035  WhatsApp alert dispatch (unit-level)
  US-041  Platform-wide analytics (admin)
"""
import pytest
from unittest.mock import patch, MagicMock

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


def _upgrade_to_pro(client, db, owner_id):
    """Upgrade an owner to Pro plan via direct DB manipulation."""
    sub = db.query(OwnerSubscription).filter(OwnerSubscription.owner_id == owner_id).first()
    pro = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == "pro").first()
    sub.plan_id = pro.id
    db.commit()


# ── US-031: Export ────────────────────────────────────────────────────────────

class TestExport:
    def test_pro_owner_can_export_fuel_as_excel(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31a@test.ci")
        owner_id = _get_user_id(owner_token)
        _upgrade_to_pro(client, db, owner_id)

        res = client.post("/api/v1/export?format=excel&type=fuel", headers=_headers(owner_token))
        assert res.status_code == 200
        assert "spreadsheetml" in res.headers["content-type"]
        assert res.headers["content-disposition"] == 'attachment; filename="carburant.xlsx"'
        assert len(res.content) > 0

    def test_pro_owner_can_export_fuel_as_pdf(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31b@test.ci")
        owner_id = _get_user_id(owner_token)
        _upgrade_to_pro(client, db, owner_id)

        res = client.post("/api/v1/export?format=pdf&type=fuel", headers=_headers(owner_token))
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.headers["content-disposition"] == 'attachment; filename="carburant.pdf"'
        assert res.content[:4] == b"%PDF"

    def test_pro_owner_can_export_maintenance_as_excel(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31c@test.ci")
        owner_id = _get_user_id(owner_token)
        _upgrade_to_pro(client, db, owner_id)

        res = client.post("/api/v1/export?format=excel&type=maintenance", headers=_headers(owner_token))
        assert res.status_code == 200
        assert "spreadsheetml" in res.headers["content-type"]

    def test_starter_owner_cannot_export(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31d@test.ci")

        res = client.post("/api/v1/export?format=excel&type=fuel", headers=_headers(owner_token))
        assert res.status_code == 403

    def test_invalid_format_returns_400(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31e@test.ci")
        owner_id = _get_user_id(owner_token)
        _upgrade_to_pro(client, db, owner_id)

        res = client.post("/api/v1/export?format=csv&type=fuel", headers=_headers(owner_token))
        assert res.status_code == 400

    def test_invalid_type_returns_400(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31f@test.ci")
        owner_id = _get_user_id(owner_token)
        _upgrade_to_pro(client, db, owner_id)

        res = client.post("/api/v1/export?format=excel&type=vehicles", headers=_headers(owner_token))
        assert res.status_code == 400

    def test_driver_cannot_export(self, client, db):
        _seed_plans(db)
        driver_token = _register_and_verify(client, db, "driver31a@test.ci", role="DRIVER")

        res = client.post("/api/v1/export?format=excel&type=fuel", headers=_headers(driver_token))
        assert res.status_code == 403

    def test_excel_export_contains_fuel_data(self, client, db):
        """Excel file is a valid workbook and contains fuel entry data."""
        from io import BytesIO
        import openpyxl
        from datetime import date
        from app.models.fuel_entry import FuelEntry
        from app.models.user import User as UserModel

        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner31g@test.ci")
        owner_id = _get_user_id(owner_token)
        _upgrade_to_pro(client, db, owner_id)

        # Add a vehicle + driver + fuel entry directly
        vehicle = Vehicle(
            owner_id=owner_id, name="Test Car", brand="Toyota", model="HiLux",
            license_plate="EXP-001-CI", fuel_type="Diesel", initial_mileage=10000,
        )
        db.add(vehicle)
        db.commit()
        driver = UserModel(
            email="d31g@test.ci", password_hash="x", role="DRIVER",
            full_name="Driver G", is_verified=True, is_active=True,
        )
        db.add(driver)
        db.commit()
        db.add(FuelEntry(
            vehicle_id=vehicle.id, driver_id=driver.id,
            date=date.today(), odometer_km=10100,
            quantity_litres="40.00", amount_fcfa="50000.00",
        ))
        db.commit()

        res = client.post("/api/v1/export?format=excel&type=fuel", headers=_headers(owner_token))
        assert res.status_code == 200
        wb = openpyxl.load_workbook(BytesIO(res.content))
        ws = wb.active
        assert ws.max_row >= 2  # header + at least one data row


# ── US-034: WhatsApp config ───────────────────────────────────────────────────

class TestWhatsAppConfig:
    def test_owner_can_set_whatsapp_number(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner34a@test.ci")

        res = client.patch(
            "/api/v1/owner/whatsapp",
            json={"whatsapp_number": "+22507000000"},
            headers=_headers(owner_token),
        )
        assert res.status_code == 200
        assert res.json()["success"] is True

    def test_owner_can_clear_whatsapp_number(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner34b@test.ci")

        # Set then clear
        client.patch("/api/v1/owner/whatsapp", json={"whatsapp_number": "+22507000000"}, headers=_headers(owner_token))
        res = client.patch("/api/v1/owner/whatsapp", json={"whatsapp_number": ""}, headers=_headers(owner_token))
        assert res.status_code == 200

        # Verify cleared in DB
        from app.models.user import User as UserModel
        owner_id = _get_user_id(owner_token)
        owner = db.get(UserModel, owner_id)
        assert owner.whatsapp_number is None

    def test_driver_cannot_configure_whatsapp(self, client, db):
        _seed_plans(db)
        driver_token = _register_and_verify(client, db, "driver34a@test.ci", role="DRIVER")

        res = client.patch(
            "/api/v1/owner/whatsapp",
            json={"whatsapp_number": "+22507000000"},
            headers=_headers(driver_token),
        )
        assert res.status_code == 403


# ── US-035: WhatsApp alert dispatch ──────────────────────────────────────────

class TestWhatsAppAlerts:
    def test_send_whatsapp_message_skips_when_not_configured(self):
        from app.services.whatsapp_service import send_whatsapp_message
        with patch("app.services.whatsapp_service.settings") as mock_settings:
            mock_settings.WHATSAPP_API_URL = ""
            mock_settings.WHATSAPP_TOKEN = ""
            result = send_whatsapp_message("+22507000000", "test")
        assert result is False

    def test_send_fleet_alerts_skips_when_no_critical_alerts(self):
        from app.services.whatsapp_service import send_fleet_alerts_to_owner
        from app.schemas.alert import AlertResponse

        warnings_only = [
            AlertResponse(
                vehicle_id=1, vehicle_name="V1", license_plate="XX",
                type="oil_change", severity="warning", message="msg", detail="det",
            )
        ]
        with patch("app.services.whatsapp_service.send_whatsapp_message") as mock_send:
            result = send_fleet_alerts_to_owner("+22507000000", "Owner", warnings_only)
        mock_send.assert_not_called()
        assert result is True

    def test_send_fleet_alerts_sends_for_critical(self):
        from app.services.whatsapp_service import send_fleet_alerts_to_owner
        from app.schemas.alert import AlertResponse

        critical_alert = AlertResponse(
            vehicle_id=1, vehicle_name="Camion 01", license_plate="AA-001-CI",
            type="insurance_expiry", severity="critical",
            message="Assurance expirée", detail="Expirée depuis 5 jours",
        )
        with patch("app.services.whatsapp_service.send_whatsapp_message", return_value=True) as mock_send:
            result = send_fleet_alerts_to_owner("+22507000000", "Jean Dupont", [critical_alert])
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert "Camion 01" in call_args[0][1]
        assert result is True

    def test_send_fleet_alerts_skips_when_no_number(self):
        from app.services.whatsapp_service import send_fleet_alerts_to_owner
        from app.schemas.alert import AlertResponse

        critical = AlertResponse(
            vehicle_id=1, vehicle_name="V1", license_plate="XX",
            type="insurance_expiry", severity="critical", message="msg", detail="det",
        )
        with patch("app.services.whatsapp_service.send_whatsapp_message") as mock_send:
            result = send_fleet_alerts_to_owner("", "Owner", [critical])
        mock_send.assert_not_called()
        assert result is False

    def test_whatsapp_api_call_uses_correct_payload(self):
        from app.services.whatsapp_service import send_whatsapp_message
        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("app.services.whatsapp_service.settings") as mock_settings, \
             patch("app.services.whatsapp_service.httpx.post", return_value=mock_response) as mock_post:
            mock_settings.WHATSAPP_API_URL = "https://graph.facebook.com/v18.0/123/messages"
            mock_settings.WHATSAPP_TOKEN = "test-token"
            send_whatsapp_message("+225 07 00 00 00", "Alerte test")

        mock_post.assert_called_once()
        _, kwargs = mock_post.call_args
        payload = kwargs["json"]
        assert payload["messaging_product"] == "whatsapp"
        assert payload["to"] == "22507000000"  # normalized
        assert payload["text"]["body"] == "Alerte test"


# ── US-041: Platform analytics ────────────────────────────────────────────────

class TestAdminAnalytics:
    def test_admin_gets_platform_stats(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin41a@test.ci")
        _register_and_verify(client, db, "owner41a@test.ci", role="OWNER")
        _register_and_verify(client, db, "driver41a@test.ci", role="DRIVER")

        res = client.get("/api/v1/admin/analytics", headers=_headers(admin_token))
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["total_owners"] >= 1
        assert data["total_drivers"] >= 1
        assert "plan_distribution" in data
        assert "new_owners_this_month" in data

    def test_analytics_counts_are_correct(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin41b@test.ci")

        before = client.get("/api/v1/admin/analytics", headers=_headers(admin_token)).json()["data"]
        prev_owners = before["total_owners"]

        _register_and_verify(client, db, "owner41b@test.ci")
        _register_and_verify(client, db, "owner41c@test.ci")

        after = client.get("/api/v1/admin/analytics", headers=_headers(admin_token)).json()["data"]
        assert after["total_owners"] == prev_owners + 2

    def test_plan_distribution_shows_starter(self, client, db):
        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin41c@test.ci")
        _register_and_verify(client, db, "owner41d@test.ci")

        res = client.get("/api/v1/admin/analytics", headers=_headers(admin_token))
        distribution = res.json()["data"]["plan_distribution"]
        names = [p["plan_name"] for p in distribution]
        assert "starter" in names

    def test_non_admin_cannot_access_analytics(self, client, db):
        _seed_plans(db)
        owner_token = _register_and_verify(client, db, "owner41e@test.ci")

        res = client.get("/api/v1/admin/analytics", headers=_headers(owner_token))
        assert res.status_code == 403

    def test_analytics_total_spend_sums_all_fuel_entries(self, client, db):
        from datetime import date
        from app.models.fuel_entry import FuelEntry
        from app.models.user import User as UserModel

        _seed_plans(db)
        admin_token = _create_admin(client, db, "sadmin41d@test.ci")

        # Get baseline
        before = client.get("/api/v1/admin/analytics", headers=_headers(admin_token)).json()["data"]
        prev_spend = before["total_spend_fcfa"]

        # Add an owner + vehicle + fuel entry
        owner_token = _register_and_verify(client, db, "owner41f@test.ci")
        owner_id = _get_user_id(owner_token)
        vehicle = Vehicle(
            owner_id=owner_id, name="V1", brand="Ford", model="Ranger",
            license_plate="AN41-CI", fuel_type="Diesel", initial_mileage=0,
        )
        db.add(vehicle)
        db.commit()
        driver = UserModel(
            email="d41f@test.ci", password_hash="x", role="DRIVER",
            full_name="D41", is_verified=True, is_active=True,
        )
        db.add(driver)
        db.commit()
        db.add(FuelEntry(
            vehicle_id=vehicle.id, driver_id=driver.id,
            date=date.today(), odometer_km=100,
            quantity_litres="30.00", amount_fcfa="25000.00",
        ))
        db.commit()

        after = client.get("/api/v1/admin/analytics", headers=_headers(admin_token)).json()["data"]
        assert after["total_spend_fcfa"] == prev_spend + 25000.0
