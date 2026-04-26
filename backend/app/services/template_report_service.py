"""
Template-based report service — deterministic Jinja2 + WeasyPrint PDF reports.

Two outputs:
  - Fleet-wide report (all vehicles, all drivers, fleet KPIs)
  - Per-driver report (one driver's activity over the period)

Both reports run for an owner-specified date range and reuse the same shared
header/footer template (templates/reports/base.html.j2).
"""

from datetime import date, datetime
from pathlib import Path
from typing import Iterable

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.fuel_entry import FuelEntry
from app.models.user import User
from app.models.vehicle import Vehicle
from app.services.alert_service import compute_alerts


TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates" / "reports"

_ALERT_TYPE_LABELS = {
    "insurance_expiry": "Assurance",
    "inspection_expiry": "Contrôle technique",
    "oil_change": "Vidange",
    "consumption_anomaly": "Consommation",
    "cost_spike": "Pic de coût",
}


# ── Jinja environment + filters ──────────────────────────────────────────────


def _format_fcfa(value) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{n:,.0f}".replace(",", " ") + " FCFA"


def _format_number(value, decimals: int = 0) -> str:
    if value is None:
        return "—"
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    return f"{n:,.{decimals}f}".replace(",", " ")


def _format_date_fr(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    return value.strftime("%d/%m/%Y")


def _build_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
    )
    env.filters["format_fcfa"] = _format_fcfa
    env.filters["format_number"] = _format_number
    env.filters["format_date_fr"] = _format_date_fr
    return env


_env = _build_env()


# ── Shared aggregation helpers ───────────────────────────────────────────────


def _fuel_query_for_owner(db: Session, owner_id: int, date_from: date, date_to: date):
    return (
        db.query(FuelEntry)
        .join(Vehicle, FuelEntry.vehicle_id == Vehicle.id)
        .filter(
            Vehicle.owner_id == owner_id,
            FuelEntry.date >= date_from,
            FuelEntry.date <= date_to,
        )
    )


def _sum_distance(entries: Iterable[FuelEntry]) -> int:
    return sum(int(e.distance_km) for e in entries if e.distance_km)


def _avg_consumption(entries: Iterable[FuelEntry]) -> float | None:
    values = [
        float(e.consumption_per_100km) for e in entries if e.consumption_per_100km
    ]
    if not values:
        return None
    return sum(values) / len(values)


def _french_month_label(year: int, month: int) -> str:
    months = [
        "janv.",
        "févr.",
        "mars",
        "avr.",
        "mai",
        "juin",
        "juil.",
        "août",
        "sept.",
        "oct.",
        "nov.",
        "déc.",
    ]
    return f"{months[month - 1]} {year}"


# ── Fleet context ────────────────────────────────────────────────────────────


def build_fleet_context(
    owner: User,
    db: Session,
    date_from: date,
    date_to: date,
) -> dict:
    entries = _fuel_query_for_owner(db, owner.id, date_from, date_to).all()

    total_spend = sum(float(e.amount_fcfa) for e in entries)
    total_litres = sum(float(e.quantity_litres) for e in entries)
    total_km = _sum_distance(entries)
    avg_consumption = _avg_consumption(entries)

    # Per-vehicle aggregation
    vehicles = (
        db.query(Vehicle)
        .filter(Vehicle.owner_id == owner.id)
        .order_by(Vehicle.name)
        .all()
    )
    by_vehicle: dict[int, list[FuelEntry]] = {v.id: [] for v in vehicles}
    for e in entries:
        by_vehicle.setdefault(e.vehicle_id, []).append(e)

    vehicle_rows = []
    for v in vehicles:
        v_entries = by_vehicle.get(v.id, [])
        if not v_entries and v.status == "archived":
            continue
        vehicle_rows.append(
            {
                "id": v.id,
                "name": v.name,
                "spend_fcfa": sum(float(e.amount_fcfa) for e in v_entries),
                "litres": sum(float(e.quantity_litres) for e in v_entries),
                "distance_km": _sum_distance(v_entries),
                "avg_consumption": _avg_consumption(v_entries),
                "entries": len(v_entries),
            }
        )
    vehicle_rows.sort(key=lambda r: r["spend_fcfa"], reverse=True)

    # Monthly trend
    monthly_rows = (
        _fuel_query_for_owner(db, owner.id, date_from, date_to)
        .with_entities(
            func.extract("year", FuelEntry.date).label("yr"),
            func.extract("month", FuelEntry.date).label("mo"),
            func.sum(FuelEntry.amount_fcfa).label("spend"),
            func.count(FuelEntry.id).label("cnt"),
        )
        .group_by("yr", "mo")
        .order_by("yr", "mo")
        .all()
    )
    max_spend = max((float(r.spend or 0) for r in monthly_rows), default=0.0)
    monthly_trend = [
        {
            "label": _french_month_label(int(r.yr), int(r.mo)),
            "spend_fcfa": float(r.spend or 0),
            "entries": int(r.cnt or 0),
            "pct": (float(r.spend or 0) / max_spend * 100) if max_spend > 0 else 0,
        }
        for r in monthly_rows
    ]

    # Drivers list (drivers who belong to this owner)
    drivers = (
        db.query(User)
        .filter(User.owner_id == owner.id, User.role == "DRIVER")
        .order_by(User.full_name)
        .all()
    )
    driver_entries: dict[int, list[FuelEntry]] = {}
    for e in entries:
        driver_entries.setdefault(e.driver_id, []).append(e)

    active_vehicle_names: dict[int, str] = {}
    av_ids = [d.active_vehicle_id for d in drivers if d.active_vehicle_id]
    if av_ids:
        for v in db.query(Vehicle).filter(Vehicle.id.in_(av_ids)).all():
            active_vehicle_names[v.id] = v.name

    driver_rows = []
    for d in drivers:
        d_entries = driver_entries.get(d.id, [])
        driver_rows.append(
            {
                "full_name": d.full_name,
                "is_disabled": d.is_disabled,
                "driving_status": d.driving_status,
                "active_vehicle_name": active_vehicle_names.get(d.active_vehicle_id),
                "entries": len(d_entries),
                "spend_fcfa": sum(float(e.amount_fcfa) for e in d_entries),
            }
        )

    # Alerts (current state — not date-bounded; reflects today's compliance)
    alerts_raw = compute_alerts(db, owner.id)
    alerts = [
        {
            "vehicle_name": a.vehicle_name,
            "type_label": _ALERT_TYPE_LABELS.get(a.type, a.type),
            "severity": a.severity,
            "message": a.message,
            "detail": a.detail,
        }
        for a in alerts_raw
    ]

    active_vehicles = sum(1 for v in vehicles if v.status == "active")
    active_drivers = sum(1 for d in drivers if not d.is_disabled)
    cost_per_km = (total_spend / total_km) if total_km else 0

    return {
        "company_name": owner.company_name or owner.full_name,
        "owner_name": owner.full_name,
        "date_from": _format_date_fr(date_from),
        "date_to": _format_date_fr(date_to),
        "generated_at": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "totals": {
            "total_spend_fcfa": total_spend,
            "total_litres": total_litres,
            "total_km": total_km,
            "avg_consumption": avg_consumption,
            "active_vehicles": active_vehicles,
            "active_drivers": active_drivers,
            "entries_count": len(entries),
            "cost_per_km": cost_per_km,
        },
        "vehicles": vehicle_rows,
        "monthly_trend": monthly_trend,
        "drivers": driver_rows,
        "alerts": alerts,
    }


# ── Driver context ───────────────────────────────────────────────────────────


def build_driver_context(
    owner: User,
    db: Session,
    driver_id: int,
    date_from: date,
    date_to: date,
) -> dict:
    driver = db.get(User, driver_id)
    if not driver or driver.role != "DRIVER" or driver.owner_id != owner.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conducteur introuvable",
        )

    entries = (
        _fuel_query_for_owner(db, owner.id, date_from, date_to)
        .filter(FuelEntry.driver_id == driver_id)
        .order_by(FuelEntry.date.desc())
        .all()
    )

    total_spend = sum(float(e.amount_fcfa) for e in entries)
    total_litres = sum(float(e.quantity_litres) for e in entries)
    total_km = _sum_distance(entries)
    avg_consumption = _avg_consumption(entries)
    avg_litres_per_entry = (total_litres / len(entries)) if entries else 0
    cost_per_km = (total_spend / total_km) if total_km else 0

    # Vehicles driven (distinct in period)
    vehicle_ids = {e.vehicle_id for e in entries}
    vehicles_map: dict[int, Vehicle] = {}
    if vehicle_ids:
        for v in db.query(Vehicle).filter(Vehicle.id.in_(vehicle_ids)).all():
            vehicles_map[v.id] = v

    vehicles_driven = []
    for vid in vehicle_ids:
        v_entries = [e for e in entries if e.vehicle_id == vid]
        v = vehicles_map.get(vid)
        vehicles_driven.append(
            {
                "name": v.name if v else f"Véhicule #{vid}",
                "entries": len(v_entries),
                "spend_fcfa": sum(float(e.amount_fcfa) for e in v_entries),
                "litres": sum(float(e.quantity_litres) for e in v_entries),
                "distance_km": _sum_distance(v_entries),
            }
        )
    vehicles_driven.sort(key=lambda r: r["spend_fcfa"], reverse=True)

    entry_rows = [
        {
            "date": _format_date_fr(e.date),
            "vehicle_name": (
                vehicles_map[e.vehicle_id].name if e.vehicle_id in vehicles_map else "—"
            ),
            "odometer_km": e.odometer_km,
            "litres": float(e.quantity_litres),
            "amount_fcfa": float(e.amount_fcfa),
            "consumption": (
                float(e.consumption_per_100km) if e.consumption_per_100km else None
            ),
        }
        for e in entries
    ]

    return {
        "company_name": owner.company_name or owner.full_name,
        "owner_name": owner.full_name,
        "date_from": _format_date_fr(date_from),
        "date_to": _format_date_fr(date_to),
        "generated_at": datetime.now().strftime("%d/%m/%Y à %H:%M"),
        "driver": {
            "full_name": driver.full_name,
            "username": driver.username,
            "phone": driver.phone,
            "is_disabled": driver.is_disabled,
            "driving_status": driver.driving_status,
        },
        "totals": {
            "total_spend_fcfa": total_spend,
            "total_litres": total_litres,
            "total_km": total_km,
            "avg_consumption": avg_consumption,
            "avg_litres_per_entry": avg_litres_per_entry,
            "cost_per_km": cost_per_km,
            "entries_count": len(entries),
        },
        "vehicles_driven": vehicles_driven,
        "entries": entry_rows,
    }


# ── Renderers ────────────────────────────────────────────────────────────────


def _render_pdf(template_name: str, context: dict) -> bytes:
    # WeasyPrint is imported lazily to keep service import lightweight in tests
    # that don't render (e.g., context-only tests can mock _render_pdf).
    from weasyprint import HTML

    html = _env.get_template(template_name).render(**context)
    return HTML(string=html).write_pdf()


def render_fleet_pdf(owner: User, db: Session, date_from: date, date_to: date) -> bytes:
    ctx = build_fleet_context(owner, db, date_from, date_to)
    return _render_pdf("fleet_report.html.j2", ctx)


def render_driver_pdf(
    owner: User,
    db: Session,
    driver_id: int,
    date_from: date,
    date_to: date,
) -> bytes:
    ctx = build_driver_context(owner, db, driver_id, date_from, date_to)
    return _render_pdf("driver_report.html.j2", ctx)
