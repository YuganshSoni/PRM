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

## Seed database

Run from the **`PRM`** directory (project root). This seeds lookup data (roles, statuses), bootstrap admin, system config, and activity tags.

```bash
cd PRM
source venv/bin/activate   # if using a virtualenv
python -m server.seed.seed_runner
```

With `python3` explicitly:

```bash
python3 -m server.seed.seed_runner
```

**Do not** run `python3 server/seed/seed_runner.py` — that fails with `ModuleNotFoundError: No module named 'server'` because Python does not add the project root to the import path. Always use `-m server.seed.seed_runner`.

Re-run safely after schema changes: seeders are idempotent (existing rows are skipped).

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

Admin (Screen 3): **Manage Employees**, **Manage Projects**, **View All Allocations**, **Manage Users**, and **System Configuration**.

Manager (Screen 4): **Resource Dashboard**, **Allocate Resource** (AI / direct / end), **My Projects**, **Timesheets**, **AI Assistant**, and **Logout**.

Employee (Screen 5): **Submit Timesheet**, **View My Timesheets**, **View My Allocations**, with missed-timesheet reminder banner on menu load.

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | (required) | Async PostgreSQL URL |
| `JWT_SECRET` | — | Use ≥ 32 characters in production |
| `JWT_EXPIRE_MINUTES` | `480` | Access token lifetime |
| `SCHEDULER_ENABLED` | `true` | Background jobs on startup |
| `CORS_ORIGINS` | empty | Comma-separated origins; empty disables CORS |
| `LOG_FORMAT` | `text` | `text` or `json` structured logs |
| `RATE_LIMIT_ENABLED` | `true` | Rate limit login + AI endpoints |
| `RATE_LIMIT_LOGIN_PER_MINUTE` | `10` | Login attempts per IP per minute |
| `RATE_LIMIT_AI_PER_MINUTE` | `20` | AI calls per IP per minute |
| `API_BASE_URL` | `http://localhost:8000` | Console client target |

## Production hardening (Phase 16)

- **Request ID:** every response includes `X-Request-ID`
- **Security headers:** `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- **Rate limiting:** `POST /auth/login`, `POST /ai/*` → 429 when exceeded
- **JWT:** stateless Bearer tokens; logout discards token client-side
- **Docker:** `docker build -t prm-api .` then run with env pointing at Postgres

```bash
# API E2E smoke (server must be running)
python -m scripts.e2e_demo_runner

# Route audit
python -m scripts.production_audit

# Lint
ruff check server client tests scripts
```

Manual console checklist: [docs/E2E_MANUAL_CHECKLIST.md](../docs/E2E_MANUAL_CHECKLIST.md)

## Engineering — SOLID (BRD §4.3)

### Single Responsibility
Each class has one reason to change — e.g. `TimesheetService` (`server/services/timesheet_service.py`) owns timesheet rules only; `AIService` orchestrates LangGraph workflows without SQL.

### Open/Closed
New LLM providers are added in `LLMFactory` (`server/ai/llm_factory.py`) without modifying `AIService` or graph nodes.

### Liskov Substitution
Repositories return consistent types (`Entity | None`); LangChain `BaseChatModel` implementations are interchangeable in chains.

### Interface Segregation
Role-specific routers expose only needed endpoints — `ConfigRouter` is Admin-only; managers use `DashboardRouter` / `AIRouter`.

### Dependency Inversion
Routers depend on `Depends(get_*_service)`; services depend on repository abstractions injected via `DependencyProvider` (`server/core/dependencies.py`).

## Design patterns

| Pattern | Location | Purpose |
|---------|----------|---------|
| Repository | `server/repositories/` | Persistence abstraction |
| Strategy | `LLMFactory` | Swappable Gemini/Groq providers |
| Factory | `ApplicationFactory`, `ScreenFactory` | App and menu wiring |
| State / Workflow | LangGraph in `server/ai/graphs/` | Skill match & risk summary pipelines |
| Dependency Injection | FastAPI `Depends()` | Session, auth, services |

## Design principles

- **Separation of Concerns:** Router → Service → Repository → DB; client screens call `HttpxClient` only
- **DRY:** `AllocationService.validate_utilisation` shared by AI-assisted and direct allocation
- **Fail Fast:** Pydantic validation + domain exceptions before DB writes or LLM calls
- **Law of Demeter:** Console never imports `server.*` modules

## Comment policy

Comments explain non-obvious business rules only (see [ENGINEERING_STANDARDS.md](../docs/ENGINEERING_STANDARDS.md)). No commented-out code or restating obvious logic.

## API overview
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
- `POST /projects` — create project (Admin only)
- `GET /projects` — list projects with SP Done/Total (Admin only)
- `GET /projects/{id}` — project detail (Admin only)
- `PUT /projects/{id}` — update project details (Admin only)
- `POST /projects/{id}/milestones` — add milestone (Admin only)
- `GET /projects/{id}/milestones` — list milestones with SP summary (Admin only)
- `PUT /milestones/{id}` — update milestone status (Admin only)
- `GET /config` — system settings (API key masked) (Admin only)
- `PUT /config` — update LLM provider/key, scheduler interval, max weekly hours (Admin only)
- `GET /allocations` — list active company-wide allocations (Admin only)
- `GET /dashboard/resources` — manager team bench, active employees, stats (Manager only)
- `GET /dashboard/employees/{id}` — team member drill-down with skills, allocations, tags (Manager only)
- `GET /projects/mine` — manager-owned projects with health snapshot (Manager only)
- `GET /projects/mine/{project_id}` — project detail: milestones, allocations, risk flags (Manager only)
- `POST /allocations` — direct allocation for own-team employee (Manager only)
- `GET /allocations/by-project/{project_id}` — active allocations on owned project (Manager only)
- `POST /allocations/{id}/end` — end allocation; owner manager only (Manager only)
- `POST /timesheets` — submit weekly timesheet with project hours and activity tags (Resource only)
- `GET /timesheets/mine` — own submitted/missed timesheet history (Resource only)
- `GET /timesheets/{id}` — own timesheet week detail (Resource or Manager for in-scope team timesheet)
- `GET /timesheets/mine/missed-reminder` — prior-week submission reminder for menu banner (Resource only)
- `GET /timesheets/team?week_start=` — manager team timesheet list by week (Manager only, read-only)
- `GET /allocations/mine` — own active allocations or week context for submit (`?week_start=`) (Employee only)
- `GET /activity-tags` — predefined activity tags for timesheet submit (Employee only)
- `POST /ai/skill-match` — rank team employees by skill/capacity for a requirement (Manager only; requires `llm_api_key` in config)
- `POST /ai/risk-summary/{project_id}` — AI narrative summary of project risks from milestones/timesheets (Manager only; owned project)

## Background scheduler (Phase 12)

- Starts automatically with `uvicorn` when `SCHEDULER_ENABLED=true` (default in `.env.example`).
- Interval: `system_config.scheduler_interval_hours` (default 4 hours); admin can change via `PUT /config`.
- Jobs each tick: recompute resource BENCH/ALLOCATED status, mark MISSED timesheets, upsert project health snapshots.
- Disable for local dev/tests: `SCHEDULER_ENABLED=false`.

Run migration after pull: `alembic upgrade head` (adds `employees.manager_id`, story point columns).

### Auth example

```bash
curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"Admin@1234"}'
```

### AI endpoints (Phase 14)

Configure LLM key first (Admin):

```bash
curl -s -X PUT http://localhost:8000/config \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"llm_api_key":"your-gemini-or-groq-key"}'
```

Skill match (Manager):

```bash
curl -s -X POST http://localhost:8000/ai/skill-match \
  -H "Authorization: Bearer $MANAGER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"requirement":"Need React developer for 3 months","project_id":1}'
```

Risk summary (Manager, owned project):

```bash
curl -s -X POST http://localhost:8000/ai/risk-summary/1 \
  -H "Authorization: Bearer $MANAGER_TOKEN"
```

### Console AI flows (Phase 15)

Manager menu:
- **Option 2 → 1** — AI-assisted allocation (project + requirement → ranked candidates → confirm allocation)
- **Option 3 → [A]** — AI risk summary on project detail
- **Option 5** — AI Assistant (standalone skill match or risk summary; `[A]` navigates to allocate with context)

Requires Admin to configure `llm_api_key` via System Configuration before AI features work.

## Verify

```bash
python scripts/verify_db.py
pytest tests/ -v

# Unit-test coverage report (HTML at htmlcov/index.html)
pytest tests/ --cov=server --cov-report=term --cov-report=html:htmlcov
```

## Bootstrap admin

- Username: `admin`
- Password: `Admin@1234` (must change on first login — Phase 2)
