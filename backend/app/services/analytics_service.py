"""
Platform analytics service — Sprint 7
  US-041  Platform-wide analytics for super admin
"""

from datetime import date

from sqlalchemy import func, extract
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.models.subscription import OwnerSubscription, SubscriptionPlan
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.analytics import AdminAnalyticsResponse, PlanDistribution


def get_platform_analytics(db: Session) -> AdminAnalyticsResponse:
    today = date.today()

    total_owners = db.query(User).filter(User.role == "OWNER").count()
    total_drivers = db.query(User).filter(User.role == "DRIVER").count()
    total_vehicles = db.query(Vehicle).filter(Vehicle.status != "archived").count()

    total_fuel_entries = db.query(func.count(FuelEntry.id)).scalar() or 0
    total_spend = db.query(func.coalesce(func.sum(FuelEntry.amount_fcfa), 0)).scalar()

    # Plan distribution — owners with an active subscription
    plan_rows = (
        db.query(SubscriptionPlan.name, func.count(OwnerSubscription.id).label("cnt"))
        .join(OwnerSubscription, OwnerSubscription.plan_id == SubscriptionPlan.id)
        .filter(OwnerSubscription.is_active.is_(True))
        .group_by(SubscriptionPlan.name)
        .order_by(SubscriptionPlan.name)
        .all()
    )
    plan_distribution = [
        PlanDistribution(plan_name=r.name, owner_count=r.cnt) for r in plan_rows
    ]

    new_owners_this_month = (
        db.query(User)
        .filter(
            User.role == "OWNER",
            extract("year", User.created_at) == today.year,
            extract("month", User.created_at) == today.month,
        )
        .count()
    )

    return AdminAnalyticsResponse(
        total_owners=total_owners,
        total_drivers=total_drivers,
        total_vehicles=total_vehicles,
        total_fuel_entries=total_fuel_entries,
        total_spend_fcfa=float(total_spend),
        plan_distribution=plan_distribution,
        new_owners_this_month=new_owners_this_month,
    )
