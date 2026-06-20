from app.models.vehicle import Vehicle  # must import before User (FK dependency)
from app.models.user import User
from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan, OwnerSubscription
from app.models.vehicle_driver import VehicleDriver
from app.models.alert_state import AlertState
from app.models.trip_log import TripLog
from app.models.maintenance_expense import MaintenanceExpense
from app.models.revenue import Revenue

__all__ = ["Vehicle", "User", "OtpCode", "SubscriptionPlan", "OwnerSubscription", "VehicleDriver", "AlertState", "TripLog", "MaintenanceExpense", "Revenue"]
