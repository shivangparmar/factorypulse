"""
schemas.py
----------
Pydantic models defining what the API actually sends/receives over HTTP.

WHY SEPARATE FROM models.py:
models.py defines DATABASE tables. schemas.py defines API CONTRACTS.
These are kept separate on purpose — it lets you, e.g., hide internal DB
fields from API responses, or accept slightly different shapes on input
than what's stored, without entangling your DB schema with your API design.
This separation is considered a FastAPI best practice.
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ---- Machine schemas ----

class MachineBase(BaseModel):
    name: str
    machine_type: str
    location: Optional[str] = None


class MachineCreate(MachineBase):
    """Shape expected when creating a new machine via POST."""
    pass


class Machine(MachineBase):
    """Shape returned by the API when reading a machine (includes DB-assigned id)."""
    id: int

    class Config:
        # Tells Pydantic it's OK to build this model from an ORM object
        # (e.g. a SQLAlchemy Machine instance) rather than only from a dict.
        from_attributes = True


# ---- Downtime event schemas ----

class DowntimeEventBase(BaseModel):
    machine_id: int
    start_time: datetime
    end_time: Optional[datetime] = None
    reason: Optional[str] = None


class DowntimeEventCreate(DowntimeEventBase):
    pass


class DowntimeEvent(DowntimeEventBase):
    id: int
    duration_minutes: Optional[float] = None

    class Config:
        from_attributes = True


# ---- Sensor reading schemas ----

class SensorReadingBase(BaseModel):
    machine_id: int
    timestamp: datetime
    value: float


class SensorReadingCreate(SensorReadingBase):
    pass


class SensorReading(SensorReadingBase):
    id: int
    is_anomaly: bool

    class Config:
        from_attributes = True


# ---- Dashboard summary schema (aggregated, not a raw table) ----

class MachineSummary(BaseModel):
    """
    Aggregated per-machine stats for the dashboard's main view.
    This isn't a DB table — it's computed on the fly in crud.py by
    joining/aggregating downtime_events and sensor_readings.
    """
    machine_id: int
    machine_name: str
    total_downtime_minutes: float
    downtime_event_count: int
    latest_anomaly: Optional[bool] = False
    uptime_percent_last_7_days: float
