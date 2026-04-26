"""
Seed script — run once after initial migration.

Usage:
  docker-compose exec backend python scripts/seed.py

What it does:
  1. Creates the 3 subscription plans (starter, pro, business)
  2. Creates the SUPER_ADMIN account (credentials from env vars or defaults)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.subscription import SubscriptionPlan

SUPER_ADMIN_EMAIL = os.getenv("SUPER_ADMIN_EMAIL", "admin@flotte225.ci")
SUPER_ADMIN_PASSWORD = os.getenv("SUPER_ADMIN_PASSWORD", "Admin@flotte225!")
SUPER_ADMIN_NAME = os.getenv("SUPER_ADMIN_NAME", "Super Admin")

PLANS = [
    {
        "name": "starter",
        "max_vehicles": 2,
        "max_drivers": 3,
        "price_fcfa": 0,
        "ai_reports_per_month": 0,
        "has_whatsapp": False,
        "has_export": False,
        "has_webhook": False,
    },
    {
        "name": "pro",
        "max_vehicles": 15,
        "max_drivers": 20,
        "price_fcfa": 9900,
        "ai_reports_per_month": 5,
        "has_whatsapp": True,
        "has_export": True,
        "has_webhook": False,
    },
    {
        "name": "business",
        "max_vehicles": None,  # unlimited
        "max_drivers": None,
        "price_fcfa": 24900,
        "ai_reports_per_month": None,  # unlimited
        "has_whatsapp": True,
        "has_export": True,
        "has_webhook": True,
    },
]


def seed():
    db = SessionLocal()
    try:
        # --- Subscription plans ---
        for plan_data in PLANS:
            existing = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == plan_data["name"]).first()
            if existing:
                print(f"  Plan '{plan_data['name']}' already exists — skipped")
            else:
                db.add(SubscriptionPlan(**plan_data))
                print(f"  Plan '{plan_data['name']}' created")
        db.commit()

        # --- Super admin account ---
        existing_admin = db.query(User).filter(User.email == SUPER_ADMIN_EMAIL).first()
        if existing_admin:
            print(f"  Super admin '{SUPER_ADMIN_EMAIL}' already exists — skipped")
        else:
            admin = User(
                email=SUPER_ADMIN_EMAIL,
                password_hash=hash_password(SUPER_ADMIN_PASSWORD),
                role="SUPER_ADMIN",
                full_name=SUPER_ADMIN_NAME,
                is_verified=True,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            print(f"  Super admin '{SUPER_ADMIN_EMAIL}' created")

        print("\nSeed complete.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
