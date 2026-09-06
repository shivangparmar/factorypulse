"""
crud.py
-------
Database query functions ("CRUD" = Create, Read, Update, Delete), plus the
aggregation logic that powers the dashboard summary endpoint.

WHY SEPARATE FROM main.py:
Keeping DB query logic out of the route handlers (main.py) means routes stay
thin and readable, and the query logic is independently testable/reusable.
This is a very common FastAPI project convention.
"""

from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from statistics import mean, pstdev

from . import models, schemas


# ---- Machines ----

def create_machine(db: Session, machine: schemas.MachineCreate) -> models.Machine:
    db_machine = models.Machine(**machine.model_dump())
    db.add(db_machine)
    db.commit()
    db.refresh(db_machine)  # refresh pulls the DB-assigned id back into the object
    return db_machine


def get_machines(db: Session):
    return db.query(models.Machine).all()


# ---- Downtime events ----

def create_downtime_event(db: Session, event: schemas.DowntimeEventCreate) -> models.DowntimeEvent:
    data = event.model_dump()

    # If both start and end times are provided up front, compute duration now
    # so it doesn't need to be recalculated on every read later.
    duration = None
    if data.get("end_time"):
        delta = data["end_time"] - data["start_time"]
        duration = round(delta.total_seconds() / 60, 1)

    db_event = models.DowntimeEvent(**data, duration_minutes=duration)
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    return db_event


def get_downtime_events(db: Session, machine_id: int | None = None):
    query = db.query(models.DowntimeEvent)
    if machine_id is not None:
        query = query.filter(models.DowntimeEvent.machine_id == machine_id)
    return query.order_by(models.DowntimeEvent.start_time.desc()).all()


# ---- Sensor readings + simple anomaly detection ----

def create_sensor_reading(db: Session, reading: schemas.SensorReadingCreate) -> models.SensorReading:
    """
    Inserts a new sensor reading and flags it as an anomaly using a simple,
    explainable rule: is this value more than 2 standard deviations from
    that machine's recent (last 50 readings) average?

    WHY A SIMPLE RULE INSTEAD OF A TRAINED MODEL FOR V1:
    A z-score threshold is transparent, requires no training data to bootstrap,
    and is enough to make the dashboard demonstrate "predictive/anomaly
    detection" convincingly. This is the natural place to later swap in a
    trained model (e.g. an autoencoder or isolation forest) without changing
    the API contract — the endpoint still just returns is_anomaly: bool.
    """
    recent_values = (
        db.query(models.SensorReading.value)
        .filter(models.SensorReading.machine_id == reading.machine_id)
        .order_by(models.SensorReading.timestamp.desc())
        .limit(50)
        .all()
    )
    recent_values = [v[0] for v in recent_values]

    is_anomaly = False
    # Need at least a handful of prior readings before z-score is meaningful;
    # otherwise a single early spike would look like an "anomaly" against no baseline.
    if len(recent_values) >= 5:
        avg = mean(recent_values)
        std = pstdev(recent_values) or 1e-6  # avoid divide-by-zero if all values are equal
        z_score = abs((reading.value - avg) / std)
        is_anomaly = z_score > 2

    db_reading = models.SensorReading(
        machine_id=reading.machine_id,
        timestamp=reading.timestamp,
        value=reading.value,
        is_anomaly=is_anomaly,
    )
    db.add(db_reading)
    db.commit()
    db.refresh(db_reading)
    return db_reading


# ---- Dashboard summary aggregation ----

def get_machine_summaries(db: Session) -> list[schemas.MachineSummary]:
    """
    Builds the per-machine summary rows the dashboard's main table/cards use.
    Computed on the fly rather than stored, since it's cheap at this data
    scale and always reflects the latest state without a sync step.
    """
    machines = db.query(models.Machine).all()
    seven_days_ago = datetime.utcnow() - timedelta(days=7)
    summaries = []

    for machine in machines:
        events = (
            db.query(models.DowntimeEvent)
            .filter(models.DowntimeEvent.machine_id == machine.id)
            .filter(models.DowntimeEvent.start_time >= seven_days_ago)
            .all()
        )
        total_downtime = sum(e.duration_minutes or 0 for e in events)

        # Simple uptime % over a 7-day window, floored at 0 in case logged
        # downtime somehow exceeds the window (bad data shouldn't show negative uptime).
        total_minutes_in_window = 7 * 24 * 60
        uptime_percent = max(0.0, round(100 * (1 - total_downtime / total_minutes_in_window), 1))

        latest_reading = (
            db.query(models.SensorReading)
            .filter(models.SensorReading.machine_id == machine.id)
            .order_by(models.SensorReading.timestamp.desc())
            .first()
        )

        summaries.append(
            schemas.MachineSummary(
                machine_id=machine.id,
                machine_name=machine.name,
                total_downtime_minutes=total_downtime,
                downtime_event_count=len(events),
                latest_anomaly=latest_reading.is_anomaly if latest_reading else False,
                uptime_percent_last_7_days=uptime_percent,
            )
        )

    return summaries
