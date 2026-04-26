from pydantic import BaseModel


class PlanDistribution(BaseModel):
    plan_name: str
    owner_count: int


class AdminAnalyticsResponse(BaseModel):
    total_owners: int
    total_drivers: int
    total_vehicles: int
    total_fuel_entries: int
    total_spend_fcfa: float
    plan_distribution: list[PlanDistribution]
    new_owners_this_month: int
