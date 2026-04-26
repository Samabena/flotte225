from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    vehicles,
    driver,
    drivers,
    fuel,
    maintenance,
    dashboard,
    admin,
    export,
    reports,
    webhook,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(drivers.router)
api_router.include_router(vehicles.router)
api_router.include_router(driver.router)
api_router.include_router(fuel.router)
api_router.include_router(maintenance.router)
api_router.include_router(dashboard.router)
api_router.include_router(admin.router)
api_router.include_router(export.router)
api_router.include_router(reports.router)
api_router.include_router(webhook.router)
