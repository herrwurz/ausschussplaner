# AGENTS.md

For project background, business logic, and standard commands, see `README.md` and `CLAUDE.md`.

## Cursor Cloud specific instructions

This is a two-part app: a **FastAPI backend** (`app/`, Python 3.12) and a **React/Vite frontend** (`frontend/`, Node 22). SQLite is embedded (file-based, auto-created + auto-seeded on backend startup) — there is no separate DB service.

### Environment
- Backend deps live in a virtualenv at `.venv` (git-ignored). The startup update script recreates/refreshes it. Always invoke Python tooling via `.venv/bin/...` (there is no `.venv/Scripts` here — that path in `CLAUDE.md`/`*.bat` is Windows-only). System has `python3` but no bare `python`.
- Frontend deps are installed under `frontend/node_modules` via `npm install` (uses `frontend/package-lock.json`).

### Running the two dev services (not started by the update script)
- Backend: `.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000` → API at `:8000` (`/health`, `/docs`).
- Frontend: `npm run dev --prefix frontend -- --host` → SPA at `:5173`. Vite proxies `/api` → `http://localhost:8000`, so the backend must be running for the SPA to work end-to-end.

### Admin login / seeding gotcha (non-obvious)
- `seed_data()` only runs when the DB is **completely empty**, and the demo admin user is only (re)created when `ADMIN_PASSWORD` is set. On an existing DB with persons but no admin, the login will fail.
- To guarantee an admin login exists, either start uvicorn with `ADMIN_EMAIL=admin@ausschussplaner.local ADMIN_PASSWORD=admin123` in the env, or run `.venv/bin/python create_admin.py` (sets/resets `admin@ausschussplaner.local` / `admin123`).
- The app also reads `SECRET_KEY` for JWT signing; set `SECRET_KEY=<anything>` in the env for production.

### Lint / test / build
- Lint: `.venv/bin/ruff check app tests` (note: the existing codebase currently reports many pre-existing ruff findings — the tooling works, the findings are not from setup).
- Tests: `.venv/bin/pytest` (uses in-memory SQLite; ~75 pass, 1 skipped).
- Frontend prod build: `npm run build --prefix frontend` → `frontend/dist`, which the backend then serves same-origin (SPA fallback in `app/main.py`).

### Hello-world check
Log in at `http://localhost:5173/admin/login` (`admin@ausschussplaner.local` / `admin123`), open the **Berechnung** tab, click **Termine berechnen** → a 2-week calendar of committee meeting proposals with TOP/BESCHLUSSFÄHIG badges appears. Equivalent API: `POST /api/calculate` with a Bearer token from `POST /api/auth/login`.
