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

## Run console client

Requires the server to be running. Set `API_BASE_URL` in `.env` if the server is not on port 8000 (e.g. `http://localhost:8005`).

```bash
# Terminal 1 — server
uvicorn server.main:app --reload

# Terminal 2 — console client
python -m client.main
```

Screen 1 flows: start menu → login → forced password change (bootstrap admin) → role stub menu → logout.

- `GET /health` — liveness
- `GET /health/db` — database connectivity
- `POST /auth/login` — authenticate (returns JWT)
- `POST /auth/change-password` — change password (Bearer token required)
- `POST /auth/logout` — logout (Bearer token required)
- `GET /auth/me` — current user profile (Bearer token required)

### Auth example

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@1234"}'
```

## Verify

```bash
python scripts/verify_db.py
pytest tests/ -v
```

## Bootstrap admin

- Username: `admin`
- Password: `Admin@1234` (must change on first login — Phase 2)
