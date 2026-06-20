"""Maintenance expense journal — per-vehicle repair/spending lines.

Owner isolation is enforced through vehicle ownership. A "Vidange" expense with
an odometer reading also advances the vehicle's last_oil_change_km, which lets
the oil-change alert resolve itself.
"""

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.maintenance import Maintenance
from app.models.maintenance_expense import MaintenanceExpense
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.schemas.maintenance_expense import (
    MaintenanceExpenseCreate,
    MaintenanceExpenseUpdate,
)


def _get_vehicle_or_404(db: Session, owner_id: int, vehicle_id: int) -> Vehicle:
    vehicle = (
        db.query(Vehicle)
        .filter(Vehicle.id == vehicle_id, Vehicle.owner_id == owner_id)
        .first()
    )
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Véhicule introuvable"
        )
    return vehicle


def _get_expense_or_404(
    db: Session, owner_id: int, expense_id: int
) -> MaintenanceExpense:
    expense = (
        db.query(MaintenanceExpense)
        .join(Vehicle, MaintenanceExpense.vehicle_id == Vehicle.id)
        .filter(MaintenanceExpense.id == expense_id, Vehicle.owner_id == owner_id)
        .first()
    )
    if not expense:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Dépense introuvable"
        )
    return expense


def _sync_oil_change(db: Session, vehicle_id: int, odometer_km: int | None) -> None:
    """A vidange at a given km advances last_oil_change_km (never backwards)."""
    if odometer_km is None:
        return
    record = (
        db.query(Maintenance).filter(Maintenance.vehicle_id == vehicle_id).first()
    )
    if record is None:
        record = Maintenance(vehicle_id=vehicle_id, last_oil_change_km=odometer_km)
        db.add(record)
        return
    if record.last_oil_change_km is None or odometer_km > record.last_oil_change_km:
        record.last_oil_change_km = odometer_km


def _assigned_or_403(db: Session, driver_id: int, vehicle_id: int) -> None:
    assignment = (
        db.query(VehicleDriver)
        .filter(
            VehicleDriver.driver_id == driver_id,
            VehicleDriver.vehicle_id == vehicle_id,
        )
        .first()
    )
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Vous n'êtes pas assigné à ce véhicule",
        )


def _persist_expense(
    db: Session, vehicle_id: int, data: MaintenanceExpenseCreate
) -> MaintenanceExpense:
    """Create the expense row + oil-change sync. Caller handles authorization.
    Idempotent on client_uuid (re-sent offline entries don't duplicate)."""
    if data.client_uuid:
        existing = (
            db.query(MaintenanceExpense)
            .filter(MaintenanceExpense.client_uuid == data.client_uuid)
            .first()
        )
        if existing:
            return existing

    expense = MaintenanceExpense(
        vehicle_id=vehicle_id,
        date=data.date,
        odometer_km=data.odometer_km,
        type=data.type,
        cost_fcfa=data.cost_fcfa,
        location=data.location,
        note=data.note,
        client_uuid=data.client_uuid,
    )
    db.add(expense)

    if data.type == "Vidange":
        _sync_oil_change(db, vehicle_id, data.odometer_km)

    db.commit()
    db.refresh(expense)
    return expense


def create_expense(
    db: Session, owner_id: int, vehicle_id: int, data: MaintenanceExpenseCreate
) -> MaintenanceExpense:
    _get_vehicle_or_404(db, owner_id, vehicle_id)
    return _persist_expense(db, vehicle_id, data)


def create_expense_as_driver(
    db: Session, driver: User, vehicle_id: int, data: MaintenanceExpenseCreate
) -> MaintenanceExpense:
    """A driver logs an expense for a vehicle they are assigned to."""
    _assigned_or_403(db, driver.id, vehicle_id)
    return _persist_expense(db, vehicle_id, data)


def list_vehicle_expenses_as_driver(
    db: Session, driver: User, vehicle_id: int
) -> list[MaintenanceExpense]:
    _assigned_or_403(db, driver.id, vehicle_id)
    return (
        db.query(MaintenanceExpense)
        .filter(MaintenanceExpense.vehicle_id == vehicle_id)
        .order_by(MaintenanceExpense.date.desc(), MaintenanceExpense.id.desc())
        .all()
    )


def list_vehicle_expenses(
    db: Session, owner_id: int, vehicle_id: int
) -> list[MaintenanceExpense]:
    _get_vehicle_or_404(db, owner_id, vehicle_id)
    return (
        db.query(MaintenanceExpense)
        .filter(MaintenanceExpense.vehicle_id == vehicle_id)
        .order_by(MaintenanceExpense.date.desc(), MaintenanceExpense.id.desc())
        .all()
    )


def list_owner_expenses(
    db: Session, owner_id: int, vehicle_id: int | None = None
) -> list[MaintenanceExpense]:
    q = (
        db.query(MaintenanceExpense)
        .join(Vehicle, MaintenanceExpense.vehicle_id == Vehicle.id)
        .filter(Vehicle.owner_id == owner_id)
    )
    if vehicle_id is not None:
        q = q.filter(MaintenanceExpense.vehicle_id == vehicle_id)
    return q.order_by(
        MaintenanceExpense.date.desc(), MaintenanceExpense.id.desc()
    ).all()


def update_expense(
    db: Session, owner_id: int, expense_id: int, data: MaintenanceExpenseUpdate
) -> MaintenanceExpense:
    expense = _get_expense_or_404(db, owner_id, expense_id)

    updates = data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(expense, field, value)
    expense.updated_at = datetime.now(timezone.utc)

    if expense.type == "Vidange":
        _sync_oil_change(db, expense.vehicle_id, expense.odometer_km)

    db.commit()
    db.refresh(expense)
    return expense


def delete_expense(db: Session, owner_id: int, expense_id: int) -> None:
    expense = _get_expense_or_404(db, owner_id, expense_id)
    db.delete(expense)
    db.commit()
