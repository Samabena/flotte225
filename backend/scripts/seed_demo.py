"""
Demo seed script — populates the database with realistic synthetic data
for Flotte225 demonstrations.

Usage:
  docker-compose exec backend python scripts/seed_demo.py

What it creates:
  Phase 1 — Structure
    - 3 owners (starter / pro / business plans)
    - 15 vehicles (5 + 8 + 2), one paused, one archived
    - 12 drivers across owners
    - driver ↔ vehicle assignments

  Phase 2 — 4 months of fuel history
    - ~250 fuel entries with realistic L/100km and FCFA amounts
    - activity logs for every entry

  Phase 3 — Maintenance
    - healthy / expiring-soon / expired scenarios per vehicle

  Phase 4 — Operational live state
    - 3 drivers currently "on duty" (driving_status=True + active_vehicle_id)
    - entries from today and yesterday (live feed)
    - cost-spike anomaly: April spend >30 % above March for Brou Kouamé
    - consumption anomaly: one vehicle's latest fill-up deviates >20 %
    - webhook state record (business owner)
    - report schedules (pro + business owners)
"""

import os
import sys
import random
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.vehicle_driver import VehicleDriver
from app.models.fuel_entry import FuelEntry
from app.models.activity_log import ActivityLog
from app.models.maintenance import Maintenance
from app.models.subscription import SubscriptionPlan, OwnerSubscription
from app.models.report_schedule import ReportSchedule
from app.models.webhook_state import WebhookState

# ── Deterministic random so reruns produce the same data ──────────────────────
random.seed(42)

TODAY = date(2026, 4, 22)
NOW = datetime(2026, 4, 22, 10, 0, 0)

# ── Helpers ───────────────────────────────────────────────────────────────────

def days_ago(n: int) -> date:
    return TODAY - timedelta(days=n)

def dt_ago(days: int = 0, hours: int = 0, minutes: int = 0) -> datetime:
    return NOW - timedelta(days=days, hours=hours, minutes=minutes)

def rand_phone() -> str:
    prefixes = ["07", "05", "01", "27", "57", "47", "77"]
    return f"+225 {random.choice(prefixes)} {random.randint(10,99)} {random.randint(10,99)} {random.randint(10,99)}"

def ci_plate(idx: int) -> str:
    letters = ["AB", "AC", "AD", "BC", "BD", "CD", "CE", "DF", "EF", "GH"]
    return f"{1000 + idx}-{letters[idx % len(letters)]}-{(idx % 5) + 1:02d}"

# ── Synthetic people & fleet ──────────────────────────────────────────────────

OWNERS = [
    {   # index 0
        "email": "konan.aya@transsud.ci",
        "password": "Demo@2026!",
        "full_name": "Konan Aya",
        "phone": "+225 07 12 34 56",
        "whatsapp_number": "+225 07 12 34 56",
        "plan": "pro",
    },
    {   # index 1
        "email": "brou.kouame@logici.ci",
        "password": "Demo@2026!",
        "full_name": "Brou Kouamé",
        "phone": "+225 05 98 76 54",
        "whatsapp_number": "+225 05 98 76 54",
        "plan": "business",
    },
    {   # index 2
        "email": "ouattara.mamadou@gmail.com",
        "password": "Demo@2026!",
        "full_name": "Ouattara Mamadou",
        "phone": "+225 01 23 45 67",
        "whatsapp_number": None,
        "plan": "starter",
    },
]

# (owner_idx, display_name, brand, model, year, fuel_type, initial_km, plate_idx, initial_status)
VEHICLES_DATA = [
    # ── Konan Aya — Pro (5 vehicles) ────────────────────────────────────────
    (0, "Land Cruiser HZJ78",   "Toyota",      "Land Cruiser HZJ78",  2019, "Diesel",   45000, 0,  "active"),
    (0, "Hilux Vigo 4x4",       "Toyota",      "Hilux Vigo",          2021, "Diesel",   28000, 1,  "active"),
    (0, "L200 Triton",          "Mitsubishi",  "L200 Triton",         2020, "Diesel",   61000, 2,  "active"),
    (0, "Peugeot 504 Pick-up",  "Peugeot",    "504 Pick-up",         2015, "Essence", 120000, 3,  "paused"),   # ← paused
    (0, "Sprinter 515 CDi",     "Mercedes",   "Sprinter 515 CDi",    2018, "Diesel",   95000, 4,  "active"),
    # ── Brou Kouamé — Business (8 vehicles) ─────────────────────────────────
    (1, "Land Cruiser 200",     "Toyota",      "Land Cruiser 200",    2022, "Diesel",   12000, 5,  "active"),
    (1, "Ranger Wildtrak",      "Ford",        "Ranger Wildtrak",     2021, "Diesel",   33000, 6,  "active"),
    (1, "Navara NP300",         "Nissan",      "Navara NP300",        2020, "Diesel",   54000, 7,  "active"),
    (1, "Amarok V6 TDI",        "Volkswagen", "Amarok V6 TDI",       2022, "Diesel",   19000, 8,  "active"),
    (1, "BT-50 Pro",            "Mazda",       "BT-50 Pro",           2019, "Diesel",   72000, 9,  "active"),
    (1, "Actyon Sports II",     "SsangYong",   "Actyon Sports II",    2018, "Diesel",   88000, 10, "active"),
    (1, "Transit Custom",       "Ford",        "Transit Custom",      2021, "Diesel",   41000, 11, "active"),
    (1, "Crafter 35 TDI",       "Volkswagen", "Crafter 35 TDI",      2020, "Diesel",   63000, 12, "archived"), # ← archived
    # ── Ouattara Mamadou — Starter (2 vehicles) ─────────────────────────────
    (2, "Corolla 2.0",          "Toyota",      "Corolla",             2018, "Essence",  78000, 13, "active"),
    (2, "Logan MCV 1.5",        "Dacia",       "Logan MCV",           2017, "Diesel",  105000, 14, "active"),
]

# (owner_idx, username, full_name, consumption_base_L100km)
DRIVERS_DATA = [
    # Konan Aya's drivers
    (0, "kone_moussa",     "Koné Moussa",      10.2),
    (0, "dosso_ibrahim",   "Dosso Ibrahim",    11.5),
    (0, "coulibaly_ali",   "Coulibaly Ali",     9.8),
    (0, "tape_serge",      "Tapé Serge",       12.1),
    # Brou Kouamé's drivers
    (1, "yao_kouassi",     "Yao Kouassi",      10.8),
    (1, "aboua_felix",     "Aboua Félix",      11.0),
    (1, "bamba_sekou",     "Bamba Sékou",       9.5),
    (1, "koffi_arnaud",    "Koffi Arnaud",     10.3),
    (1, "traore_adama",    "Traoré Adama",     11.8),
    (1, "gbe_patrice",     "Gbé Patrice",      10.1),
    # Ouattara Mamadou's drivers
    (2, "ouattara_seydou", "Ouattara Seydou",   8.9),
    (2, "diallo_moussa",   "Diallo Moussa",     9.4),
]

# vehicle_index → [local driver indices inside owner's driver list]
ASSIGNMENTS = {
    0: [0, 1],   # Land Cruiser → Koné Moussa, Dosso Ibrahim
    1: [1, 2],   # Hilux → Dosso Ibrahim, Coulibaly Ali
    2: [2, 3],   # L200 → Coulibaly Ali, Tapé Serge
    3: [3],      # 504 Pick-up → Tapé Serge  (paused vehicle, still has history)
    4: [0, 3],   # Sprinter → Koné Moussa, Tapé Serge
    5: [4, 5],   # LC200 → Yao Kouassi, Aboua Félix
    6: [5, 6],   # Ranger → Aboua Félix, Bamba Sékou
    7: [6, 7],   # Navara → Bamba Sékou, Koffi Arnaud
    8: [7, 8],   # Amarok → Koffi Arnaud, Traoré Adama
    9: [8, 9],   # BT-50 → Traoré Adama, Gbé Patrice
    10: [4, 9],  # Actyon → Yao Kouassi, Gbé Patrice
    11: [5, 7],  # Transit → Aboua Félix, Koffi Arnaud
    12: [6, 8],  # Crafter (archived) → Bamba Sékou, Traoré Adama
    13: [10],    # Corolla → Ouattara Seydou
    14: [11],    # Logan → Diallo Moussa
}

# Fuel price per litre in FCFA
FUEL_PRICES = {"Essence": 870, "Diesel": 710, "GPL": 540}

# (vehicle_idx, oil_km_offset, insurance_expiry_offset_days, inspection_expiry_offset_days)
MAINTENANCE_DATA = [
    (0,  -200,  +120, +200),   # healthy
    (1,  -800,   +45,  +90),   # insurance expiring in 45 days  ← ATTENTION
    (2,  -500,   -15,  +60),   # insurance EXPIRED 15 days ago  ← CRITIQUE
    (3,  -200,  +200,  -30),   # inspection EXPIRED 30 days ago ← CRITIQUE (paused vehicle)
    (4,  -600,   +30,  +30),   # both expiring in 30 days       ← ATTENTION x2
    (5,  -300,  +180, +365),   # healthy
    (6,  -400,   +90, +120),   # healthy
    (7,  -700,   -10,  +45),   # insurance EXPIRED 10 days ago  ← CRITIQUE
    (8,  -200,   +60,  +60),   # healthy
    (9,  -900,   +20,   -7),   # inspection EXPIRED 7 days ago  ← CRITIQUE
    (10, -100,  +150, +200),   # healthy
    (11, -500,   +45,  +90),   # insurance expiring soon         ← ATTENTION
    (12, -300,  +200, +300),   # archived vehicle
    (13, -600,   +30,  +60),   # insurance expiring soon         ← ATTENTION
    (14, -400,    -5, +120),   # insurance EXPIRED 5 days ago   ← CRITIQUE
]

# ── Fuel history builder ──────────────────────────────────────────────────────

def build_fuel_history(vehicle, assigned_drivers: list):
    """
    Generate ~4 months of fill-up records.
    Returns list of (FuelEntry, driver) tuples — not yet added to session.
    """
    entries = []
    fill_interval_days = random.randint(6, 10)
    num_fills = int(120 / fill_interval_days)
    base_consumption = random.uniform(9.5, 12.0)

    odometer = vehicle.initial_mileage
    current_day = 120

    for i in range(num_fills):
        driver = assigned_drivers[i % len(assigned_drivers)]
        entry_date = days_ago(current_day)
        entry_dt = dt_ago(days=current_day, hours=random.randint(0, 10))

        distance = random.randint(80, 300)
        consumption = base_consumption * random.uniform(0.85, 1.15)
        litres = round((distance * consumption) / 100, 2)
        amount = round(litres * FUEL_PRICES[vehicle.fuel_type] * random.uniform(0.98, 1.02), 2)
        odometer += distance

        distance_km = None if i == 0 else distance
        cons_per_100 = None if i == 0 else round((litres / distance) * 100, 2)

        entry = FuelEntry(
            vehicle_id=vehicle.id,
            driver_id=driver.id,
            date=entry_date,
            odometer_km=odometer,
            quantity_litres=Decimal(str(litres)),
            amount_fcfa=Decimal(str(amount)),
            distance_km=distance_km,
            consumption_per_100km=Decimal(str(cons_per_100)) if cons_per_100 else None,
            created_at=entry_dt,
            updated_at=entry_dt,
        )
        entries.append((entry, driver))
        current_day -= fill_interval_days + random.randint(-1, 2)
        if current_day < 0:
            break

    return entries


def add_activity_log(db, owner_id, driver_id, vehicle_id, entry, action="CREATE"):
    after = {
        "odometer_km":      entry.odometer_km,
        "quantity_litres":  float(entry.quantity_litres),
        "amount_fcfa":      float(entry.amount_fcfa),
        "date":             str(entry.date),
    }
    db.add(ActivityLog(
        owner_id=owner_id,
        driver_id=driver_id,
        vehicle_id=vehicle_id,
        fuel_entry_id=entry.id,
        action=action,
        data_before=None,
        data_after=after,
        created_at=entry.created_at,
    ))


def entry_exists(db, vehicle_id, entry_date, odometer_km) -> bool:
    return bool(
        db.query(FuelEntry)
        .filter(
            FuelEntry.vehicle_id == vehicle_id,
            FuelEntry.date == entry_date,
            FuelEntry.odometer_km == odometer_km,
        )
        .first()
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def seed_demo():
    db = SessionLocal()
    try:
        print("\n=== Flotte225 Demo Seed ===\n")

        # ── Plans (must exist — run seed.py first) ────────────────────────────
        plans = {}
        for name in ["starter", "pro", "business"]:
            plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.name == name).first()
            if not plan:
                print(f"  ERROR: plan '{name}' not found — run seed.py first")
                return
            plans[name] = plan
        print("  Plans loaded ✓")

        # ── PHASE 1: Owners ───────────────────────────────────────────────────
        print("\n--- Phase 1: owners & subscriptions ---")
        owner_records = []
        for od in OWNERS:
            existing = db.query(User).filter(User.email == od["email"]).first()
            if existing:
                print(f"  {od['full_name']} already exists — skipped")
                owner_records.append(existing)
                continue

            owner = User(
                email=od["email"],
                password_hash=hash_password(od["password"]),
                role="OWNER",
                full_name=od["full_name"],
                phone=od["phone"],
                whatsapp_number=od["whatsapp_number"],
                is_verified=True,
                is_active=True,
                created_at=dt_ago(days=130),
                updated_at=dt_ago(days=130),
            )
            db.add(owner)
            db.flush()

            db.add(OwnerSubscription(
                owner_id=owner.id,
                plan_id=plans[od["plan"]].id,
                started_at=dt_ago(days=130),
                expires_at=None if od["plan"] == "starter" else dt_ago(days=-90),
                is_active=True,
                assigned_by=None,
                created_at=dt_ago(days=130),
                updated_at=dt_ago(days=130),
            ))
            db.flush()
            owner_records.append(owner)
            print(f"  Owner: {od['full_name']} ({od['plan']})")

        db.commit()

        # ── PHASE 1: Vehicles ─────────────────────────────────────────────────
        print("\n--- Phase 1: vehicles ---")
        vehicle_records = []
        for vi, (owner_idx, vname, brand, model, year, fuel_type, init_km, plate_idx, v_status) in enumerate(VEHICLES_DATA):
            owner = owner_records[owner_idx]
            plate = ci_plate(plate_idx)
            existing = db.query(Vehicle).filter(Vehicle.license_plate == plate).first()
            if existing:
                print(f"  {vname} [{plate}] already exists — skipped")
                vehicle_records.append(existing)
                continue

            vehicle = Vehicle(
                owner_id=owner.id,
                name=vname,
                brand=brand,
                model=model,
                year=year,
                license_plate=plate,
                vin=f"VIN{plate_idx:03d}CI2026XY{1000+vi}",
                fuel_type=fuel_type,
                initial_mileage=init_km,
                status=v_status,
                archived_at=dt_ago(days=10) if v_status == "archived" else None,
                created_at=dt_ago(days=125),
                updated_at=dt_ago(days=10 if v_status == "archived" else 125),
            )
            db.add(vehicle)
            db.flush()
            vehicle_records.append(vehicle)
            status_label = f" [{v_status.upper()}]" if v_status != "active" else ""
            print(f"  Vehicle: {vname} [{plate}]{status_label} → {owner.full_name}")

        db.commit()

        # ── PHASE 1: Drivers ──────────────────────────────────────────────────
        print("\n--- Phase 1: drivers ---")
        driver_records_by_owner: dict[int, list] = {0: [], 1: [], 2: []}
        for owner_idx, username, full_name, _ in DRIVERS_DATA:
            owner = owner_records[owner_idx]
            existing = db.query(User).filter(User.username == username).first()
            if existing:
                print(f"  @{username} already exists — skipped")
                driver_records_by_owner[owner_idx].append(existing)
                continue

            driver = User(
                username=username,
                password_hash=hash_password("Driver@2026!"),
                role="DRIVER",
                full_name=full_name,
                phone=rand_phone(),
                owner_id=owner.id,
                is_verified=True,
                is_active=True,
                is_disabled=False,
                driving_status=False,
                created_at=dt_ago(days=120),
                updated_at=dt_ago(days=120),
            )
            db.add(driver)
            db.flush()
            driver_records_by_owner[owner_idx].append(driver)
            print(f"  Driver: {full_name} (@{username}) → {owner.full_name}")

        db.commit()

        # ── PHASE 1: Assignments ──────────────────────────────────────────────
        print("\n--- Phase 1: vehicle-driver assignments ---")
        for vi, local_indices in ASSIGNMENTS.items():
            vehicle = vehicle_records[vi]
            owner_idx = VEHICLES_DATA[vi][0]
            owner_drivers = driver_records_by_owner[owner_idx]
            for li in local_indices:
                driver = owner_drivers[li % len(owner_drivers)]
                exists = (
                    db.query(VehicleDriver)
                    .filter(VehicleDriver.vehicle_id == vehicle.id,
                            VehicleDriver.driver_id == driver.id)
                    .first()
                )
                if not exists:
                    db.add(VehicleDriver(
                        vehicle_id=vehicle.id,
                        driver_id=driver.id,
                        assigned_at=dt_ago(days=115),
                    ))
        db.commit()
        print("  Assignments done ✓")

        # ── PHASE 2: Fuel history (4 months) ─────────────────────────────────
        print("\n--- Phase 2: fuel history (4 months) ---")
        total_entries = 0
        for vi, (owner_idx, vname, *_) in enumerate(VEHICLES_DATA):
            vehicle = vehicle_records[vi]
            owner = owner_records[owner_idx]
            owner_drivers = driver_records_by_owner[owner_idx]
            local_indices = ASSIGNMENTS.get(vi, [0])
            assigned_drivers = [owner_drivers[i % len(owner_drivers)] for i in local_indices]

            pairs = build_fuel_history(vehicle, assigned_drivers)
            for entry, driver in pairs:
                if entry_exists(db, vehicle.id, entry.date, entry.odometer_km):
                    continue
                db.add(entry)
                db.flush()
                add_activity_log(db, owner.id, driver.id, vehicle.id, entry)
                total_entries += 1
            db.commit()

        print(f"  Fuel entries created: {total_entries}")

        # ── PHASE 3: Maintenance records ──────────────────────────────────────
        print("\n--- Phase 3: maintenance records ---")
        for vi, oil_offset, ins_days, insp_days in MAINTENANCE_DATA:
            vehicle = vehicle_records[vi]
            existing = db.query(Maintenance).filter(Maintenance.vehicle_id == vehicle.id).first()
            if existing:
                print(f"  Maintenance vehicle #{vi} already exists — skipped")
                continue
            latest = (
                db.query(FuelEntry)
                .filter(FuelEntry.vehicle_id == vehicle.id)
                .order_by(FuelEntry.odometer_km.desc())
                .first()
            )
            current_km = latest.odometer_km if latest else vehicle.initial_mileage
            oil_km = max(0, current_km + oil_offset)

            # Determine label for output
            ins_label = f"expires in {ins_days}d" if ins_days > 0 else f"EXPIRED {-ins_days}d ago"
            insp_label = f"expires in {insp_days}d" if insp_days > 0 else f"EXPIRED {-insp_days}d ago"

            db.add(Maintenance(
                vehicle_id=vehicle.id,
                last_oil_change_km=oil_km,
                insurance_expiry=TODAY + timedelta(days=ins_days),
                inspection_expiry=TODAY + timedelta(days=insp_days),
                created_at=dt_ago(days=100),
                updated_at=dt_ago(days=5),
            ))
            print(f"  {VEHICLES_DATA[vi][1]}: oil@{oil_km}km | insurance {ins_label} | inspection {insp_label}")
        db.commit()

        # ── PHASE 4: Operational live state ──────────────────────────────────
        print("\n--- Phase 4: live operational state ---")

        # 4a. Active driving sessions —————————————————————————————————————————
        # 3 drivers are currently on duty right now
        # (vehicle_idx, driver_local_idx, owner_idx)
        ACTIVE_SESSIONS = [
            (0, 0, 0),   # Land Cruiser HZJ78 ← Koné Moussa   (Konan Aya)
            (5, 0, 1),   # Land Cruiser 200   ← Yao Kouassi    (Brou Kouamé)
            (13, 0, 2),  # Corolla 2.0        ← Ouattara Seydou (Ouattara Mamadou)
        ]
        for vi, li, oi in ACTIVE_SESSIONS:
            vehicle = vehicle_records[vi]
            driver = driver_records_by_owner[oi][li]
            if driver.driving_status and driver.active_vehicle_id == vehicle.id:
                print(f"  {driver.full_name} already on duty — skipped")
                continue
            driver.driving_status = True
            driver.active_vehicle_id = vehicle.id
            driver.updated_at = dt_ago(hours=2)
            print(f"  ON DUTY: {driver.full_name} → {vehicle.name}")
        db.commit()

        # 4b. Very recent fuel entries (today & yesterday) ————————————————————
        # These make the activity feed feel alive
        LIVE_ENTRIES = [
            # (vehicle_idx, driver_local_idx, owner_idx, hours_ago, distance_km, litres, notes)
            (0, 1, 0, 1,  180, 19.8,  "Land Cruiser — Dosso Ibrahim, 1 h ago"),
            (6, 0, 1, 3,  220, 24.2,  "Ranger Wildtrak — Aboua Félix, 3 h ago"),
            (8, 0, 1, 5,  160, 17.6,  "Amarok — Koffi Arnaud, 5 h ago"),
            (1, 0, 0, 26, 200, 22.0,  "Hilux — Koné Moussa, yesterday"),
            (5, 1, 1, 28, 190, 20.9,  "LC200 — Aboua Félix, yesterday"),
            (14, 0, 2, 30, 140, 13.2, "Logan — Diallo Moussa, yesterday"),
        ]

        for vi, li, oi, hours_ago_val, distance, litres, notes in LIVE_ENTRIES:
            vehicle = vehicle_records[vi]
            owner   = owner_records[oi]
            driver  = driver_records_by_owner[oi][li % len(driver_records_by_owner[oi])]
            entry_dt = dt_ago(hours=hours_ago_val)
            entry_date = entry_dt.date()
            amount = round(litres * FUEL_PRICES[vehicle.fuel_type] * random.uniform(0.98, 1.02), 2)

            latest = (
                db.query(FuelEntry)
                .filter(FuelEntry.vehicle_id == vehicle.id)
                .order_by(FuelEntry.odometer_km.desc())
                .first()
            )
            prev_odometer = latest.odometer_km if latest else vehicle.initial_mileage
            new_odometer = prev_odometer + distance
            cons = round((litres / distance) * 100, 2)

            if not entry_exists(db, vehicle.id, entry_date, new_odometer):
                entry = FuelEntry(
                    vehicle_id=vehicle.id,
                    driver_id=driver.id,
                    date=entry_date,
                    odometer_km=new_odometer,
                    quantity_litres=Decimal(str(litres)),
                    amount_fcfa=Decimal(str(amount)),
                    distance_km=distance,
                    consumption_per_100km=Decimal(str(cons)),
                    created_at=entry_dt,
                    updated_at=entry_dt,
                )
                db.add(entry)
                db.flush()
                add_activity_log(db, owner.id, driver.id, vehicle.id, entry)
                print(f"  Live entry: {notes}")
        db.commit()

        # 4c. Cost-spike anomaly for Brou Kouamé —————————————————————————————
        # April spend must be > 30 % above March for at least one vehicle
        # We add 6 high-value entries in April for vehicles 5 and 6
        print("\n  [anomaly] Seeding cost-spike for Brou Kouamé (April vs March)...")
        SPIKE_ENTRIES = [
            (5, 0, 1, 15, 350, 39.2),   # LC200, 15 days ago
            (5, 1, 1, 10, 380, 42.5),
            (5, 0, 1,  5, 360, 40.1),
            (6, 0, 1, 14, 340, 37.4),   # Ranger, 14 days ago
            (6, 1, 1,  9, 370, 41.0),
            (6, 0, 1,  4, 355, 39.6),
        ]
        for vi, li, oi, days_ago_val, distance, litres in SPIKE_ENTRIES:
            vehicle = vehicle_records[vi]
            owner   = owner_records[oi]
            driver  = driver_records_by_owner[oi][li % len(driver_records_by_owner[oi])]
            entry_date = days_ago(days_ago_val)
            entry_dt   = dt_ago(days=days_ago_val, hours=8)
            amount = round(litres * FUEL_PRICES[vehicle.fuel_type] * 1.0, 2)

            latest = (
                db.query(FuelEntry)
                .filter(FuelEntry.vehicle_id == vehicle.id)
                .order_by(FuelEntry.odometer_km.desc())
                .first()
            )
            prev_odometer = latest.odometer_km if latest else vehicle.initial_mileage
            new_odometer = prev_odometer + distance
            cons = round((litres / distance) * 100, 2)

            if not entry_exists(db, vehicle.id, entry_date, new_odometer):
                entry = FuelEntry(
                    vehicle_id=vehicle.id,
                    driver_id=driver.id,
                    date=entry_date,
                    odometer_km=new_odometer,
                    quantity_litres=Decimal(str(litres)),
                    amount_fcfa=Decimal(str(amount)),
                    distance_km=distance,
                    consumption_per_100km=Decimal(str(cons)),
                    created_at=entry_dt,
                    updated_at=entry_dt,
                )
                db.add(entry)
                db.flush()
                add_activity_log(db, owner.id, driver.id, vehicle.id, entry)
        db.commit()
        print("  Cost-spike entries done ✓")

        # 4d. Consumption anomaly for BT-50 Pro (vehicle 9) ——————————————————
        # Add one entry with ~40 % higher consumption than average (~11 → ~15.4 L/100km)
        print("\n  [anomaly] Seeding consumption anomaly for BT-50 Pro...")
        vehicle = vehicle_records[9]
        owner   = owner_records[1]
        driver  = driver_records_by_owner[1][4]  # Traoré Adama
        latest = (
            db.query(FuelEntry)
            .filter(FuelEntry.vehicle_id == vehicle.id)
            .order_by(FuelEntry.odometer_km.desc())
            .first()
        )
        prev_odometer = latest.odometer_km if latest else vehicle.initial_mileage
        anom_distance = 120
        anom_litres = 18.5   # ~15.4 L/100km vs ~11 baseline → +40 %
        anom_odometer = prev_odometer + anom_distance
        anom_date = days_ago(2)
        anom_dt = dt_ago(days=2, hours=14)
        anom_cons = round((anom_litres / anom_distance) * 100, 2)
        anom_amount = round(anom_litres * FUEL_PRICES[vehicle.fuel_type], 2)

        if not entry_exists(db, vehicle.id, anom_date, anom_odometer):
            entry = FuelEntry(
                vehicle_id=vehicle.id,
                driver_id=driver.id,
                date=anom_date,
                odometer_km=anom_odometer,
                quantity_litres=Decimal(str(anom_litres)),
                amount_fcfa=Decimal(str(anom_amount)),
                distance_km=anom_distance,
                consumption_per_100km=Decimal(str(anom_cons)),
                created_at=anom_dt,
                updated_at=anom_dt,
            )
            db.add(entry)
            db.flush()
            add_activity_log(db, owner.id, driver.id, vehicle.id, entry)
            print(f"  Anomaly entry: BT-50 Pro — {anom_cons} L/100km (Traoré Adama)")
        db.commit()

        # 4e. Webhook state (business owner) ——————————————————————————————————
        brou = owner_records[1]
        ws = db.query(WebhookState).filter(WebhookState.owner_id == brou.id).first()
        if not ws:
            db.add(WebhookState(
                owner_id=brou.id,
                last_sent_at=dt_ago(days=1, hours=6),
                last_status_code=200,
                created_at=dt_ago(days=90),
                updated_at=dt_ago(days=1, hours=6),
            ))
            db.commit()
            print("\n  Webhook state created for Brou Kouamé ✓")

        # 4f. Report schedules (pro & business owners) —————————————————————————
        for i, od in enumerate(OWNERS):
            if od["plan"] == "starter":
                continue
            owner = owner_records[i]
            exists = db.query(ReportSchedule).filter(ReportSchedule.owner_id == owner.id).first()
            if exists:
                continue
            freq = "monthly" if od["plan"] == "pro" else "weekly"
            db.add(ReportSchedule(
                owner_id=owner.id,
                enabled=True,
                frequency=freq,
                last_sent_at=dt_ago(days=7),
                last_status="sent",
                ai_reports_used_month=random.randint(1, 3),
                usage_reset_at=TODAY.replace(day=1),
                created_at=dt_ago(days=100),
                updated_at=dt_ago(days=7),
            ))
        db.commit()
        print("  Report schedules done ✓")

        # 4g. One edited + one deleted entry to show UPDATE & DELETE in activity log
        print("\n  [activity] Seeding UPDATE & DELETE log entries...")
        # Grab an older entry on vehicle 7 (Navara) and simulate an edit
        navara = vehicle_records[7]
        brou   = owner_records[1]
        some_entry = (
            db.query(FuelEntry)
            .filter(FuelEntry.vehicle_id == navara.id)
            .order_by(FuelEntry.created_at)
            .offset(2)
            .first()
        )
        if some_entry:
            before_snap = {
                "odometer_km":     some_entry.odometer_km,
                "quantity_litres": float(some_entry.quantity_litres),
                "amount_fcfa":     float(some_entry.amount_fcfa),
                "date":            str(some_entry.date),
            }
            after_snap = dict(before_snap)
            after_snap["quantity_litres"] = round(float(some_entry.quantity_litres) + 1.5, 2)
            after_snap["amount_fcfa"]     = round(after_snap["quantity_litres"] * FUEL_PRICES[navara.fuel_type], 2)

            edit_log_exists = (
                db.query(ActivityLog)
                .filter(
                    ActivityLog.fuel_entry_id == some_entry.id,
                    ActivityLog.action == "UPDATE",
                )
                .first()
            )
            if not edit_log_exists:
                db.add(ActivityLog(
                    owner_id=brou.id,
                    driver_id=some_entry.driver_id,
                    vehicle_id=navara.id,
                    fuel_entry_id=some_entry.id,
                    action="UPDATE",
                    data_before=before_snap,
                    data_after=after_snap,
                    created_at=dt_ago(days=10, hours=3),
                ))
                print("  UPDATE log entry added (Navara NP300)")

        # Simulate a DELETE log (entry removed, fuel_entry_id stays as None per model design)
        transit = vehicle_records[11]
        del_entry = (
            db.query(FuelEntry)
            .filter(FuelEntry.vehicle_id == transit.id)
            .order_by(FuelEntry.created_at)
            .first()
        )
        if del_entry:
            del_log_exists = (
                db.query(ActivityLog)
                .filter(
                    ActivityLog.vehicle_id == transit.id,
                    ActivityLog.action == "DELETE",
                )
                .first()
            )
            if not del_log_exists:
                before_snap = {
                    "odometer_km":     del_entry.odometer_km,
                    "quantity_litres": float(del_entry.quantity_litres),
                    "amount_fcfa":     float(del_entry.amount_fcfa),
                    "date":            str(del_entry.date),
                }
                db.add(ActivityLog(
                    owner_id=brou.id,
                    driver_id=del_entry.driver_id,
                    vehicle_id=transit.id,
                    fuel_entry_id=None,   # entry "deleted"
                    action="DELETE",
                    data_before=before_snap,
                    data_after=None,
                    created_at=dt_ago(days=8, hours=1),
                ))
                print("  DELETE log entry added (Transit Custom)")

        db.commit()

        # ── Summary ───────────────────────────────────────────────────────────
        print("\n" + "=" * 60)
        print("✔  Demo seed complete.")
        print("=" * 60)
        print()
        print("DEMO CREDENTIALS")
        print("-" * 60)
        print(f"{'Role':<22} {'Login':<34} {'Password'}")
        print("-" * 60)
        for od in OWNERS:
            plan = od['plan'].upper()
            print(f"OWNER ({plan:<8})       {od['email']:<34} {od['password']}")
        print()
        for owner_idx, username, full_name, _ in DRIVERS_DATA:
            owner_name = OWNERS[owner_idx]['full_name'].split()[0]
            print(f"DRIVER ({owner_name:<12})  @{username:<33} Driver@2026!")
        print("-" * 60)
        print()
        print("DEMO SCENARIOS READY")
        print("-" * 60)
        print("  Vehicles:    13 active | 1 paused | 1 archived")
        print("  Drivers:     3 currently ON DUTY (driving_status=true)")
        print("  Alerts:      4x insurance/inspection EXPIRED | 4x expiring soon")
        print("  Anomaly:     BT-50 Pro consumption spike (~15.4 L/100km vs ~11 avg)")
        print("  Cost spike:  April vs March +30 %+ for Brou Kouamé")
        print("  Activity:    CREATE / UPDATE / DELETE all present in audit log")
        print("  Webhook:     last dispatch 1 day ago, HTTP 200")
        print("-" * 60)

    except Exception as exc:
        db.rollback()
        raise exc
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo()
