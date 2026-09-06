# FactoryPulse — Industrial Operations Analytics for MSMEs

## The problem
Small and mid-sized manufacturers (MSMEs) rarely have visibility into machine
downtime and equipment health. Enterprise-grade industrial IoT platforms are
built (and priced) for large factories, leaving smaller operations tracking
breakdowns on paper or not at all — which means costly failures go unseen
until they've already stopped production.

## What FactoryPulse does
FactoryPulse is a lightweight ops-analytics platform that gives a factory
floor manager a single dashboard showing, per machine:
- **Uptime %** over a rolling 7-day window
- **Downtime event history** (frequency, duration, and cause)
- **An early-warning anomaly flag**, computed from sensor readings, so a
  machine trending toward failure gets noticed before it actually breaks down

## Architecture
```
Next.js (frontend dashboard)
        │  HTTP/JSON
        ▼
FastAPI (REST API, this repo)
        │
        ▼
PostgreSQL (machines, downtime_events, sensor_readings)
```

- **Backend**: FastAPI + SQLAlchemy + PostgreSQL (falls back to SQLite for
  zero-setup local development)
- **Anomaly detection**: a transparent z-score rule (>2 standard deviations
  from a machine's own recent baseline) flags at-risk readings — chosen for
  v1 because it's explainable and needs no training data to bootstrap. The
  `/sensor-readings` endpoint is the natural place to swap in a trained model
  later without changing the API contract.
- **Frontend**: Next.js dashboard (separate repo/folder), calling the single
  `/dashboard/summary` endpoint for its main view.

## What's in this repo
```
factorypulse/
├── app/
│   ├── main.py       — FastAPI routes
│   ├── models.py     — SQLAlchemy table definitions
│   ├── schemas.py     — Pydantic request/response contracts
│   ├── crud.py        — DB queries + anomaly detection logic
│   └── database.py    — DB connection/session setup
├── seed_data.py        — generates realistic synthetic demo data
├── requirements.txt
└── .env.example
```

## Running it locally
```bash
pip install -r requirements.txt
python seed_data.py          # populates demo data (auto-creates tables)
uvicorn app.main:app --reload
```
Then visit `http://127.0.0.1:8000/docs` for interactive API docs, or
`http://127.0.0.1:8000/dashboard/summary` for the raw dashboard data.

No Postgres install required for local dev — it falls back to SQLite
automatically. Set `DATABASE_URL` (see `.env.example`) to point at Postgres
for production.

## Live demo
[link to be added after deployment]

## Roadmap
- Deploy backend (Railway) + frontend (Vercel)
- Replace z-score rule with a trained anomaly-detection model
- Add production-count and quality-defect tracking
- Multi-plant / multi-tenant support
