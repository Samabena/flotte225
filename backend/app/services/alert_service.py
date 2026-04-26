"""
Alert engine — computes alerts dynamically from maintenance records and fuel entries.

US-016: Oil change alert (km-based)
US-026: Insurance / inspection expiry alerts (date-based)
US-027: Consumption anomaly (>20% deviation from vehicle average)
US-028: Monthly cost spike (current month >30% above last month)
"""

from datetime import date
from sqlalchemy.orm import Session
from sqlalchemy import func, extract

from app.models.vehicle import Vehicle
from app.models.maintenance import Maintenance
from app.models.fuel_entry import FuelEntry
from app.schemas.alert import AlertResponse


# ── helpers ───────────────────────────────────────────────────────────────────


def _days_until(d: date) -> int:
    return (d - date.today()).days


def _latest_odometer(db: Session, vehicle_id: int) -> int | None:
    result = (
        db.query(func.max(FuelEntry.odometer_km))
        .filter(FuelEntry.vehicle_id == vehicle_id)
        .scalar()
    )
    return result


# ── US-026: Compliance date alerts ───────────────────────────────────────────


def _compliance_alerts(
    vehicle: Vehicle, record: Maintenance | None
) -> list[AlertResponse]:
    if record is None:
        return []
    alerts: list[AlertResponse] = []

    for field, label, alert_type in [
        (record.insurance_expiry, "assurance", "insurance_expiry"),
        (record.inspection_expiry, "contrôle technique", "inspection_expiry"),
    ]:
        if field is None:
            continue
        days = _days_until(field)
        if days < 0:
            alerts.append(
                AlertResponse(
                    vehicle_id=vehicle.id,
                    vehicle_name=vehicle.name,
                    license_plate=vehicle.license_plate,
                    type=alert_type,
                    severity="critical",
                    message=f"{label.capitalize()} expirée",
                    detail=f"Expirée depuis {abs(days)} jour(s) (le {field})",
                )
            )
        elif days <= 30:
            alerts.append(
                AlertResponse(
                    vehicle_id=vehicle.id,
                    vehicle_name=vehicle.name,
                    license_plate=vehicle.license_plate,
                    type=alert_type,
                    severity="warning",
                    message=f"{label.capitalize()} bientôt expirée",
                    detail=f"Expire dans {days} jour(s) (le {field})",
                )
            )
    return alerts


# ── US-016: Oil change alert ──────────────────────────────────────────────────


def _oil_change_alert(
    db: Session, vehicle: Vehicle, record: Maintenance | None
) -> AlertResponse | None:
    if record is None or record.last_oil_change_km is None:
        return None
    latest = _latest_odometer(db, vehicle.id)
    if latest is None:
        return None
    km_since = latest - record.last_oil_change_km
    if km_since < 400:
        return None
    severity = "critical" if km_since >= 500 else "warning"
    return AlertResponse(
        vehicle_id=vehicle.id,
        vehicle_name=vehicle.name,
        license_plate=vehicle.license_plate,
        type="oil_change",
        severity=severity,
        message=(
            "Vidange requise" if severity == "critical" else "Vidange bientôt requise"
        ),
        detail=f"{km_since} km parcourus depuis la dernière vidange (seuil : 500 km)",
    )


# ── US-027: Consumption anomaly ───────────────────────────────────────────────


def _consumption_anomaly(db: Session, vehicle: Vehicle) -> AlertResponse | None:
    entries = (
        db.query(FuelEntry)
        .filter(
            FuelEntry.vehicle_id == vehicle.id,
            FuelEntry.consumption_per_100km.isnot(None),
        )
        .order_by(FuelEntry.created_at.asc())
        .all()
    )
    if len(entries) < 2:
        return None
    latest = entries[-1]
    historical = entries[:-1]
    avg = sum(float(e.consumption_per_100km) for e in historical) / len(historical)
    latest_val = float(latest.consumption_per_100km)
    if avg == 0:
        return None
    deviation = abs(latest_val - avg) / avg
    if deviation <= 0.20:
        return None
    direction = "élevée" if latest_val > avg else "faible"
    return AlertResponse(
        vehicle_id=vehicle.id,
        vehicle_name=vehicle.name,
        license_plate=vehicle.license_plate,
        type="consumption_anomaly",
        severity="warning",
        message="Consommation anormale détectée",
        detail=f"Dernière consommation : {latest_val:.2f} L/100km (moyenne : {avg:.2f} L/100km) — {round(deviation * 100)}% trop {direction}",
    )


# ── US-028: Monthly cost spike ────────────────────────────────────────────────


def _cost_spike(db: Session, vehicle: Vehicle) -> AlertResponse | None:
    today = date.today()
    current_month = today.month
    current_year = today.year
    last_month = current_month - 1 if current_month > 1 else 12
    last_year = current_year if current_month > 1 else current_year - 1

    def _month_total(year: int, month: int) -> float:
        result = (
            db.query(func.sum(FuelEntry.amount_fcfa))
            .filter(
                FuelEntry.vehicle_id == vehicle.id,
                extract("year", FuelEntry.date) == year,
                extract("month", FuelEntry.date) == month,
            )
            .scalar()
        )
        return float(result) if result else 0.0

    current_total = _month_total(current_year, current_month)
    last_total = _month_total(last_year, last_month)

    if last_total == 0:
        return None
    spike = (current_total - last_total) / last_total
    if spike <= 0.30:
        return None
    return AlertResponse(
        vehicle_id=vehicle.id,
        vehicle_name=vehicle.name,
        license_plate=vehicle.license_plate,
        type="cost_spike",
        severity="warning",
        message="Pic de coût carburant détecté",
        detail=f"Ce mois-ci : {current_total:,.0f} FCFA — mois dernier : {last_total:,.0f} FCFA (+{round(spike * 100)}%)",
    )


# ── Main entry point ──────────────────────────────────────────────────────────


def compute_alerts(db: Session, owner_id: int) -> list[AlertResponse]:
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.owner_id == owner_id, Vehicle.status == "active")
        .all()
    )

    alerts: list[AlertResponse] = []
    for vehicle in vehicles:
        record = (
            db.query(Maintenance).filter(Maintenance.vehicle_id == vehicle.id).first()
        )

        alerts.extend(_compliance_alerts(vehicle, record))

        oil_alert = _oil_change_alert(db, vehicle, record)
        if oil_alert:
            alerts.append(oil_alert)

        anomaly = _consumption_anomaly(db, vehicle)
        if anomaly:
            alerts.append(anomaly)

        spike = _cost_spike(db, vehicle)
        if spike:
            alerts.append(spike)

    return alerts
