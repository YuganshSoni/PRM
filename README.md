# PRM Tool

Project & Resource Management — FastAPI backend with async PostgreSQL.

## Prerequisites

- Python 3.12
- Docker (for local PostgreSQL on port **5433**)

## Setup

```bash
cd PRM
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
docker compose up -d db
alembic upgrade head
python -m server.seed.seed_runner
```

## Run server

```bash
uvicorn server.main:app --reload
```

- `GET /health` — liveness
- `GET /health/db` — database connectivity

## Verify

```bash
python scripts/verify_db.py
pytest tests/ -v
```

## Bootstrap admin

- Username: `admin`
- Password: `Admin@1234` (must change on first login — Phase 2)
