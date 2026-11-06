# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Produzzy is a multi-workspace SaaS for inventory, labels and replenishment, running in production. Each workspace is a company, team or stock context, and all business data must stay isolated by `workspace_id`.

**Visual system:** the redesign is complete. `docs/redesign/REDESIGN.md` (tokens, shared components, responsive rules) and `docs/redesign/prototipo.html` (visual reference) remain the reference for any new UI, so new screens match the rest of the app.

## Layout

Monorepo with two independent apps:

- `backend/` — Python, FastAPI + SQLAlchemy + Alembic + Pydantic, PostgreSQL primary. JWT via `python-jose`, passwords via `passlib`/bcrypt, `qrcode`/Pillow/`python-barcode` for labels. Run commands from inside `backend/`.
- `frontend/` — React 19 + Vite, plain JS/JSX (no TypeScript), plain CSS, no component library. Routing with `react-router-dom`.

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

Request flow: `routers/<domain>.py` → `crud` → SQLAlchemy models.

- **Routers are thin.** They live under `/workspaces/{workspace_id}/...` (except `auth`), resolve `get_current_user` / `get_db` from `dependencies.py`, call `crud.require_workspace_role(workspace_id, user, db, <ROLE_SET>)`, then delegate to a `crud` function. Add new endpoints following this exact shape.
- **`app/crud/` is the business layer** — a package split by domain (`users`, `workspaces`, `invites`, `products`, `stock`, `categories`, `replenishment`, `dashboard`, `search`, `audit`, shared helpers in `base`), all re-exported from `app/crud/__init__.py` so routers call `crud.<function>`. It holds all permission checks, `workspace_id` filtering, stock-movement recording, soft delete, replenishment transitions, and audit logging. Role sets are module constants in `app/crud/base.py` (`READ_ROLES`, `PRODUCT_WRITE_ROLES`, `STOCK_WRITE_ROLES`, etc.); reuse them, don't inline role lists.
- **`main.py`** builds the app, CORS from `PRODUZZY_ALLOWED_ORIGINS`, an HTTP-timing middleware (`X-Process-Time-Ms`), and `/health` + `/ready` probes. Register every new router here.
- **`config.py`** reads all `PRODUZZY_*` env vars (loaded from `backend/.env`).
- **`database.py`** — `engine`, `SessionLocal`, `Base`, plus Postgres connection-pool tuning from `DB_POOL_*` env vars. PostgreSQL is the real target; SQLite is only legacy compatibility and must not guide new decisions.
- **`models.py`** (SQLAlchemy models) and **`schemas.py`** (Pydantic schemas and enums).
- **Schema changes go through Alembic** (`backend/alembic/versions/`) and only when the schema genuinely changes. Revision ids must be ≤ 32 chars (`alembic_version.version_num` is `varchar(32)`); follow the `NNNN_short_slug` pattern of existing files.
- `services/` — `security_service` (JWT/passwords), `google_auth_service`, `rate_limit_service`, `qrcode_service` (QR codes + printable labels), `avatar_storage_service` (Cloudinary).

## Frontend architecture

- **Routing is `react-router-dom`.** `App.jsx` composes providers (`ThemeProvider` → `AuthProvider` → `WorkspaceProvider`) and declares the routes: public ones (`/login`, `/forgot-password`, `/reset-password/:token`, `/verify-email/:token`, `/termos`, `/privacidade`, invite links `/invites/:token/accept` and `/join/:token`) and the authenticated ones inside `AppLayout` (`/dashboard`, `/stock`, `/production`, `/labels`, `/settings`). `Sidebar` uses `NavLink`. Server state uses TanStack Query (`@tanstack/react-query`) on some pages.
- **Contexts** (`contexts/`): `AuthContext` (session/user, login/logout), `WorkspaceContext` (workspace list + `activeWorkspace`, remounted per-user via a `key`), `ThemeContext` (persisted light/dark).
- **Data access is layered**: `pages`/`components` call `services/<domain>Service.js`, which call `request` / `requestBlob` from `lib/api.js`. `lib/api.js` owns the base URL (`VITE_API_URL`), bearer-token storage (session vs. local storage = "remember me"), 401 handling (`onUnauthorized` clears token + notifies), and a `ApiError` with a PT-BR message map. Add new endpoints as a service function, not a raw `fetch`.
- `components/ui/` reusable primitives, `components/layout/` shell + workspace modals/menus, `components/replenishment/` the replenishment flow. `lib/formatters.js` and `lib/replenishment.js` hold shared display/domain helpers. All styling is `src/styles/global.css` — match existing patterns, no CSS-in-JS or UI kit.

## Domain rules

These are invariants. Do not break them without an explicit request.

### Workspaces and permissions

- Every business read or write must check workspace membership and filter by `workspace_id`. Never allow cross-workspace reads or mutations.
- Access levels (`WorkspaceMember.role`): `owner` (UI: crown, "Responsável pelo workspace"), `admin` (Administração), `manager` (Gestão), `employee` (Operação), `requester` (Solicitante), `viewer` (Visualizador). Preserve the permission matrix in `app/crud/base.py`:
  - read: all levels;
  - products/categories: `owner`, `admin`, `manager`;
  - stock: `owner`, `admin`, `manager`, `employee`;
  - replenishments: create by `owner`, `admin`, `manager`, `employee`, `requester`; update/assign by `owner`, `admin`, `manager`, `employee`; managing assignees by `owner`, `admin`, `manager`; only `owner`/`admin`/`manager`/`employee` can be assignees; assignees and the creator can comment;
  - members, cargos and invites: `owner`, `admin` (an admin only manages `manager`/`employee`/`requester`/`viewer`);
  - audit logs: `owner`, `admin`, `manager`.
- Cargos (`WorkspaceMember.title`) define the access level through `WORKSPACE_MEMBER_TITLE_ROLES` in `app/crud/base.py` (mirrored in `frontend/src/lib/formatters.js`). Setting a cargo sets the role; the owner keeps `owner` whatever cargo they show. Only the owner assigns Administração cargos.
- Protect owners: never remove or demote the last owner of a workspace. Ownership only moves through `POST /workspaces/{id}/transfer-ownership` (main owner, confirmed by the workspace name).

### Stock

- Stock can never go negative; outgoing moves larger than the current stock are rejected.
- Stock only changes through a real stock movement, and every change creates a `stock_movements` row preserving `quantity_before`, `quantity_after`, user, product, workspace and an audit log.
- Creating a replenishment, or marking it `completed`, does not change stock.
- Inactive products cannot have stock moved.

### Replenishment

- Main flow: `open` → `in_progress` → `completed` → `stocked`. `canceled` is an alternative terminal state.
- A replenishment only becomes `stocked` when a real stock entry is linked to it.
- Active replenishments (`open`, `in_progress`, `completed`) block a duplicate for the same product in the same workspace.
- Assignees must be members of the same workspace, and cannot change once the replenishment is `completed`, `stocked` or `canceled`.

### Products and categories

- Products use soft delete (`is_active`, `deleted_at`, `deleted_by_user_id`) and keep their movement history.
- Categories use soft delete and may soft-delete linked products, preserving `deleted_by_category_id`.
- Restores must respect the uniqueness of active names per workspace.
- Deleted products/categories must not appear in active listings, dashboard, low stock, labels or QR codes, unless the flow explicitly asks for `include_deleted` / the matching status.

### Audit logs

- Preserve existing audit logs and create one for every relevant mutation. Never delete, retroactively mask or rewrite audit history without an explicit request.
- Keep audit metadata small and free of passwords, hashes, JWTs, invite tokens, secrets or unnecessary sensitive data.

## Security and configuration

- Never print or expose secrets, tokens, passwords, hashes or real `.env` contents, and don't edit `.env` without an explicit request.
- Only update `.env.example` when a documented public variable is actually added or changed.
- Never point tests at the development or production database: `DATABASE_URL_TEST` must differ from `DATABASE_URL`.

## Deployment

Hosted on Render, with PostgreSQL on Neon. `render.yaml` (repo root) is the Blueprint; `DEPLOY.md` is the operational checklist (required env vars, `alembic upgrade head` as pre-deploy, `/health` as health check, SPA rewrite for the frontend). `backend/Procfile` is a fallback for Procfile-based platforms.

## Conventions

- Do not commit or push automatically.
- Keep changes small and scoped to the request; no large refactors, new dependencies or migrations without a real need. Preserve existing architecture and visual patterns.
- Backend user-facing strings and API error `detail`s are Portuguese.
- Before finishing: run `npm run lint` and `npm run build` after frontend changes, `python -m pytest` (plus checks relevant to the area) after backend changes, and `git diff --check`; review the diff. If a check can't run, say why.
- End every task by reporting: what was done, files changed, checks run, errors or warnings, remaining risks, and recommended manual checks.
