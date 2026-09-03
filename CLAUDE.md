# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read this first

`AGENTS.md` at the repo root contains the authoritative, detailed domain rules (permission matrix, stock invariants, replenishment state machine, soft-delete semantics, audit-log constraints, change/validation policy). Follow it. This file covers the parts not in `AGENTS.md`: commands and cross-file architecture.

`.atlas/` holds product/roadmap notes (`PRODUCT.md`, `ROADMAP.md`, `STATE.md`) and logs written by a separate automation tool — read for product context, don't treat as code.

## Layout

Monorepo with two independent apps:

- `backend/` — FastAPI + SQLAlchemy + Alembic, PostgreSQL primary. Run commands from inside `backend/`.
- `frontend/` — React 19 + Vite, plain JS/JSX, plain CSS, no component library, no router library.

## Commands

### Backend (run from `backend/`)

```bash
source venv/bin/activate            # or use venv/bin/python directly
pip install -r requirements.txt
alembic upgrade head                # apply migrations
uvicorn app.main:app --reload       # dev server on :8000, docs at /docs

python -m pytest                    # full test suite
python -m pytest tests/test_permissions.py::test_name   # single test
python -m compileall app alembic tests                  # syntax check
alembic current / alembic heads     # inspect migration state
```

Tests are **integration tests against a real PostgreSQL database**. They are skipped unless `DATABASE_URL_TEST` is set, and refuse to run if it equals `DATABASE_URL`. `conftest.py` runs Alembic migrations once per session, then `TRUNCATE ... RESTART IDENTITY CASCADE` before and after every test. Fixtures: `client`, `user_factory`, `workspace_factory`, `workspace_member_factory(owner_headers, workspace_id, role)`.

### Frontend (run from `frontend/`)

```bash
npm install
npm run dev        # Vite dev server on :5173
npm run lint       # eslint . — run after any frontend change
npm run build      # run after any frontend change
```

## Backend architecture

Request flow: `routers/<domain>.py` → `crud.py` → SQLAlchemy models.

- **Routers are thin.** They live under `/workspaces/{workspace_id}/...` (except `auth`), resolve `get_current_user` / `get_db` from `dependencies.py`, call `crud.require_workspace_role(workspace_id, user, db, <ROLE_SET>)`, then delegate to a `crud` function. Add new endpoints following this exact shape.
- **`crud.py` (~3k lines) is the business layer** — all permission checks, `workspace_id` filtering, stock-movement recording, soft delete, replenishment transitions, and audit logging. Role sets are module constants (`READ_ROLES`, `PRODUCT_WRITE_ROLES`, `STOCK_WRITE_ROLES`, etc.); reuse them, don't inline role lists.
- **`main.py`** builds the app, CORS from `PRODUZZY_ALLOWED_ORIGINS`, an HTTP-timing middleware (`X-Process-Time-Ms`), and `/health` + `/ready` probes. Register every new router here.
- **`config.py`** reads all `PRODUZZY_*` env vars (loaded from `backend/.env`). Never print or edit secrets; only touch `.env.example` when a documented public var actually changes.
- **`database.py`** — `engine`, `SessionLocal`, `Base`. Contains a legacy SQLite-only dev path (`ensure_development_schema`, column back-fills). PostgreSQL is the real target; do not design around SQLite.
- **Schema changes go through Alembic** (`backend/alembic/versions/`) and only when the schema genuinely changes. Revision ids must be ≤ 32 chars (`alembic_version.version_num` is `varchar(32)`); follow the `NNNN_short_slug` pattern of existing files.
- `services/` — `security_service` (JWT/passwords), `google_auth_service`, `rate_limit_service`, `qrcode_service` (QR codes + printable labels), `avatar_storage_service` (Cloudinary).

## Frontend architecture

- **No routing library.** `App.jsx` composes providers (`ThemeProvider` → `AuthProvider` → `WorkspaceProvider`) and does its own navigation: `activePage` state maps through `pageComponents` to a `pages/*` screen; `AppLayout` + `Sidebar` switch pages via `onNavigate`. The only URL-driven views are invite links (`/invites/:token/accept`, `/join/:token`), parsed from `window.location.pathname` and cleared with `history.replaceState`.
- **Contexts** (`contexts/`): `AuthContext` (session/user, login/logout), `WorkspaceContext` (workspace list + `activeWorkspace`, remounted per-user via a `key`), `ThemeContext` (persisted light/dark).
- **Data access is layered**: `pages`/`components` call `services/<domain>Service.js`, which call `request` / `requestBlob` from `lib/api.js`. `lib/api.js` owns the base URL (`VITE_API_URL`), bearer-token storage (session vs. local storage = "remember me"), 401 handling (`onUnauthorized` clears token + notifies), and a `ApiError` with a PT-BR message map. Add new endpoints as a service function, not a raw `fetch`.
- `components/ui/` reusable primitives, `components/layout/` shell + workspace modals/menus, `components/replenishment/` the replenishment flow. `lib/formatters.js` and `lib/replenishment.js` hold shared display/domain helpers. All styling is `src/styles/global.css` — match existing patterns, no CSS-in-JS or UI kit.

## Deployment

Hosted on Render. `render.yaml` (repo root) is the Blueprint; `DEPLOY.md` is the operational checklist (required env vars, `alembic upgrade head` as pre-deploy, `/health` as health check, SPA rewrite for the frontend). `backend/Procfile` is a fallback for Procfile-based platforms.

## Conventions

- Do not commit or push automatically. Keep changes small and scoped to the request.
- Backend user-facing strings and API error `detail`s are Portuguese.
- Every business read/write must be workspace-scoped; never allow cross-workspace access. See `AGENTS.md` for the full rule set and the required end-of-task report format.
