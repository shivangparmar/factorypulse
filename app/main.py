"""
main.py
-------
The FastAPI application entrypoint: defines routes and wires them to crud.py.

RUN LOCALLY WITH:
    uvicorn app.main:app --reload
Then visit http://127.0.0.1:8000/docs for interactive Swagger UI — this
auto-generated docs page is itself a nice thing to show off in a demo video,
since it proves the API is real and typed, not mocked.
"""

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

from . import models, schemas, crud
from .database import engine, get_db

# Creates all tables defined in models.py if they don't already exist.
# Fine for a v1 project; a production app would use a migration tool
# like Alembic instead so schema changes are tracked and reversible.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="FactoryPulse API",
    description="Industrial operations analytics for MSMEs — machine uptime, downtime, and anomaly tracking.",
    version="0.1.0",
)

# CORS: allows the Next.js frontend (running on a different domain/port)
# to call this API from the browser. Wide open here for demo simplicity —
# in a real production app you'd restrict allow_origins to your actual
# frontend domain instead of "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Simple health-check endpoint — useful for confirming deployment worked."""
    return {"status": "FactoryPulse API is running"}


# ---- Machines ----

@app.post("/machines", response_model=schemas.Machine)
def create_machine(machine: schemas.MachineCreate, db: Session = Depends(get_db)):
    return crud.create_machine(db, machine)


@app.get("/machines", response_model=List[schemas.Machine])
def list_machines(db: Session = Depends(get_db)):
    return crud.get_machines(db)


# ---- Downtime events ----

@app.post("/downtime-events", response_model=schemas.DowntimeEvent)
def create_downtime_event(event: schemas.DowntimeEventCreate, db: Session = Depends(get_db)):
    return crud.create_downtime_event(db, event)


@app.get("/downtime-events", response_model=List[schemas.DowntimeEvent])
def list_downtime_events(machine_id: int | None = None, db: Session = Depends(get_db)):
    return crud.get_downtime_events(db, machine_id)


# ---- Sensor readings ----

@app.post("/sensor-readings", response_model=schemas.SensorReading)
def create_sensor_reading(reading: schemas.SensorReadingCreate, db: Session = Depends(get_db)):
    return crud.create_sensor_reading(db, reading)


# ---- Dashboard summary (the endpoint the Next.js frontend will call most) ----

@app.get("/dashboard/summary", response_model=List[schemas.MachineSummary])
def dashboard_summary(db: Session = Depends(get_db)):
    """
    Returns one summary row per machine: downtime totals, uptime %, and
    latest anomaly flag. This is the single endpoint the frontend dashboard
    page will call to render its main view.
    """
    return crud.get_machine_summaries(db)
