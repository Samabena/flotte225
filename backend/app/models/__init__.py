from app.models.vehicle import Vehicle  # must import before User (FK dependency)
from app.models.user import User
from app.models.otp_code import OtpCode
from app.models.subscription import SubscriptionPlan, OwnerSubscription
from app.models.vehicle_driver import VehicleDriver
