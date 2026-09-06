"""
database.py
------------
Sets up the SQLAlchemy engine, session, and declarative base used across the app.

WHY THIS STRUCTURE:
FastAPI apps typically separate "how we connect to the DB" (this file) from
"what our tables look like" (models.py) and "what data shapes the API exposes"
(schemas.py). This keeps concerns isolated so you can, e.g., swap Postgres for
SQLite in tests without touching your table definitions.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# DATABASE_URL is read from an environment variable rather than hardcoded.
# This is standard practice: it lets you use a local Postgres URL during dev
# and a different one (e.g. Railway's managed Postgres) in production, without
# changing code. See .env.example for the expected format.
#
# Falls back to a local SQLite file if no env var is set, so you can run this
# immediately without installing Postgres first, then swap in real Postgres
# once you deploy.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./factorypulse.db")
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+pg8000://", 1)
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+pg8000://", 1)

# connect_args is only needed for SQLite (it disallows multi-threaded access
# by default, which FastAPI's async nature can trip over). Postgres doesn't
# need this, so we conditionally apply it.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)

# SessionLocal is a factory for DB sessions. Each API request will get its own
# session (see get_db() dependency in main.py) so requests don't share state.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base is the class all our ORM models (in models.py) will inherit from.
# SQLAlchemy uses this to know which classes map to which tables.
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that yields a DB session and guarantees it's closed
    after the request finishes, even if an error occurs.
    Used via `Depends(get_db)` in route functions.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
