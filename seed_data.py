"""
seed_data.py
------------
Populates the database with plausible synthetic MSME factory data so the
dashboard looks real to anyone viewing the demo (recruiters won't have
actual factory data to upload themselves).

RUN WITH:
    python seed_data.py
(after the API has been started at least once so tables exist, or run
`python -c "from app.database import engine, Base; from app import models; Base.metadata.create_all(engine)"`
first if you want to seed before ever starting the server.)

DESIGN NOTE:
We generate ~14 days of sensor readings per machine with a few deliberately
injected anomalies/spikes, plus a handful of downtime events with varied
reasons. This gives the dashboard something interesting to show — a few
"Attention" flags, some downtime history to chart — rather than an empty
or perfectly uniform dataset that looks fake.
"""

import random
from datetime import datetime, timedelta

from app.database import SessionLocal, engine, Base
from app import models

# Ensure tables exist before we try to insert into them.
Base.metadata.create_all(bind=engine)

db = SessionLocal()

MACHINE_DEFS = [
    ("CNC Lathe 1", "CNC", "Bay 1"),
    ("CNC Lathe 2", "CNC", "Bay 1"),
    ("Packaging Line A", "Packaging", "Bay 2"),
    ("Air Compressor 1", "Compressor", "Utility Room"),
    ("Injection Molder 1", "Molding", "Bay 3"),
]

DOWNTIME_REASONS = [
    "mechanical failure",
    "power cut",
    "scheduled maintenance",
    "operator changeover",
    "material shortage",
]


def seed():
    # Wipe existing demo data so this script is safely re-runnable without
    # producing duplicate machines each time you run it.
    db.query(models.SensorReading).delete()
    db.query(models.DowntimeEvent).delete()
    db.query(models.Machine).delete()
    db.commit()

    machines = []
    for name, mtype, location in MACHINE_DEFS:
        m = models.Machine(name=name, machine_type=mtype, location=location)
        db.add(m)
        machines.append(m)
    db.commit()
    for m in machines:
        db.refresh(m)

    now = datetime.utcnow()

    for machine in machines:
        # --- Sensor readings: one every ~4 hours for the last 14 days ---
        baseline = random.uniform(40, 60)  # each machine has its own "normal" baseline
        num_readings = 14 * 6  # 6 readings/day
        for i in range(num_readings):
            ts = now - timedelta(hours=4 * (num_readings - i))
            # Normal readings cluster near baseline with small noise.
            value = baseline + random.gauss(0, 2)

            # Deliberately inject a handful of anomalous spikes so the
            # z-score logic in crud.py has something real to flag.
            if random.random() < 0.03:
                value += random.choice([-1, 1]) * random.uniform(15, 25)

            reading = models.SensorReading(machine_id=machine.id, timestamp=ts, value=value)
            db.add(reading)

        # --- Downtime events: 2-6 random events over the last 14 days ---
        for _ in range(random.randint(2, 6)):
            start = now - timedelta(
                days=random.uniform(0, 14),
                hours=random.uniform(0, 24),
            )
            duration_minutes = random.uniform(10, 180)
            end = start + timedelta(minutes=duration_minutes)
            event = models.DowntimeEvent(
                machine_id=machine.id,
                start_time=start,
                end_time=end,
                reason=random.choice(DOWNTIME_REASONS),
                duration_minutes=round(duration_minutes, 1),
            )
            db.add(event)

    db.commit()
    print(f"Seeded {len(machines)} machines with sensor readings and downtime events.")


if __name__ == "__main__":
    seed()
    db.close()
