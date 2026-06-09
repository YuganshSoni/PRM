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

Screen 1 flows: start menu → login → forced password change (bootstrap admin) → role menu → logout.

Admin (Screen 3): **Manage Employees** (view/filter, update profile, deactivate, skills, assign manager) and **Manage Users** (create, view, reset password, deactivate, reactivate). Other admin options stubbed until Phases 6–7.

- `GET /health` — liveness
- `GET /health/db` — database connectivity
- `POST /auth/login` — authenticate (returns JWT)
- `POST /auth/change-password` — change password (Bearer token required)
- `POST /auth/logout` — logout (Bearer token required)
- `GET /auth/me` — current user profile (Bearer token required)
- `POST /users` — create user account (Admin only)
- `GET /users` — list users with active/inactive counts (Admin only)
- `GET /users/lookup?identifier=` — find user by username or ID (Admin only)
- `POST /users/{id}/reset-password` — reset temp password (Admin only)
- `POST /users/{id}/deactivate` — deactivate user (Admin only)
- `POST /users/{id}/reactivate` — reactivate user (Admin only)
- `PUT /employees/by-user/{user_id}` — create or update employee profile (Admin only)
- `GET /employees` — list employees with bench/allocated counts (Admin only)
- `GET /employees/{id}` — employee detail with active allocations (Admin only)
- `POST /employees/{id}/deactivate` — deactivate employee cascade (Admin only)
- `PUT /employees/assign-manager` — assign reporting manager (Admin only)
- `POST /employees/{id}/skills` — add skill (Admin only)
- `GET /employees/{id}/skills` — list skills (Admin only)
- `PUT /skills/{id}` — update skill proficiency (Admin only)
- `DELETE /skills/{id}` — remove skill (Admin only)

Run migration after pull: `alembic upgrade head` (adds `employees.manager_id`).

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
