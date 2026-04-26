from pydantic import BaseModel


class AlertResponse(BaseModel):
    vehicle_id: int
    vehicle_name: str
    license_plate: str
    type: str  # insurance_expiry | inspection_expiry | oil_change | consumption_anomaly | cost_spike
    severity: str  # warning | critical
    message: str
    detail: str
