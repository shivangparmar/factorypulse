"""
models.py
---------
SQLAlchemy ORM models: the actual database tables.

SCOPE DECISION FOR V1:
Rather than modeling the whole "industrial ops platform" (production counts,
quality defects, multiple plants, shifts, etc.) we're deliberately starting
with ONE clear, demoable story: machine uptime/downtime tracking with a
simple anomaly flag. This is the thin vertical slice — it's easier to deploy,
easier to demo, and still shows the same engineering skills (relational
modeling, timestamps, foreign keys, status logic) as a bigger system would.
You can expand the schema later without breaking this core.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime

from .database import Base


class Machine(Base):
    """
    Represents a single piece of factory equipment being monitored.
    In a real MSME deployment, each row here = one physical machine on the
    floor (e.g. a CNC lathe, a packaging line, a compressor).
    """
    __tablename__ = "machines"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)           # e.g. "CNC Lathe 3"
    machine_type = Column(String, nullable=False)     # e.g. "CNC", "Packaging", "Compressor"
    location = Column(String, nullable=True)          # e.g. "Bay 2"

    # A machine has many downtime events (one-to-many relationship).
    # `back_populates` links this to the `machine` attribute on DowntimeEvent below,
    # so you can access `machine.downtime_events` or `event.machine` in either direction.
    downtime_events = relationship("DowntimeEvent", back_populates="machine")
    readings = relationship("SensorReading", back_populates="machine")


class DowntimeEvent(Base):
    """
    A single recorded instance of a machine stopping unexpectedly.
    This is the core "signal" the dashboard will visualize — frequency,
    duration, and cause of downtime per machine.
    """
    __tablename__ = "downtime_events"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)

    start_time = Column(DateTime, nullable=False, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)  # null while downtime is ongoing

    reason = Column(String, nullable=True)  # e.g. "mechanical failure", "power cut", "unknown"

    # duration_minutes is stored explicitly (rather than always computed from
    # start/end) so completed historical events remain queryable/chartable
    # even if end_time logic changes later. Computed at write-time in crud.py.
    duration_minutes = Column(Float, nullable=True)

    machine = relationship("Machine", back_populates="downtime_events")


class SensorReading(Base):
    """
    A lightweight time-series reading from a machine (e.g. temperature,
    vibration, or a simple 'health score'). This is what powers the
    predictive/anomaly-flag story — a real ML model or even a simple
    threshold rule can watch this table and flag risk before a breakdown.

    Kept intentionally simple for v1: one generic numeric value + a flag,
    rather than many sensor-specific columns. Easy to extend later.
    """
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    machine_id = Column(Integer, ForeignKey("machines.id"), nullable=False)

    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    value = Column(Float, nullable=False)          # e.g. a vibration/health score
    is_anomaly = Column(Boolean, default=False)     # flagged by the predictive logic

    machine = relationship("Machine", back_populates="readings")
