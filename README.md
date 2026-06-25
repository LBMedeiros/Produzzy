# Produzzy API

Produzzy API is an MVP backend for inventory and production control. It is built as a multi-workspace SaaS foundation, so multiple companies, teams, or stock locations can use the same API while keeping their data isolated.

## Features

- JWT authentication with Swagger Authorize support.
- User registration, login, token generation, and current-user lookup.
- Workspaces for company/team/stock isolation.
- Workspace members with roles: `owner`, `admin`, `employee`, and `viewer`.
- Invite flow without email delivery: the API returns an invite token and symbolic accept URL.
- Workspace-scoped product and category management.
- Workspace-scoped stock movements with authenticated user audit fields.
- Low-stock product listing per workspace.
- Dashboard summary per workspace.
- Product QR Code generation with workspace-scoped URLs.
- Individual product label generation.
- A4 label sheet generation per workspace.
- Simple pagination for products, categories, stock movements, members, and invites.

## Tech Stack

- Python
- FastAPI
- SQLAlchemy
- SQLite for local development
- Pydantic
- JWT with `python-jose`
- Password hashing with `passlib` and bcrypt
- `python-dotenv` for local environment variables
- `qrcode` and Pillow for QR Code and label images
- Uvicorn

## Project Structure

```text
app/
  config.py                 Environment configuration
  crud.py                   Database operations, workspace rules, and permissions
  database.py               SQLAlchemy engine, session, and local schema helpers
  dependencies.py           FastAPI dependencies for database and auth
  main.py                   FastAPI application setup
  models.py                 SQLAlchemy models
  schemas.py                Pydantic request and response schemas
  routers/
    auth.py                 Authentication routes
    workspaces.py           Workspace, member, and invite routes
    categories.py           Workspace-scoped category routes
    dashboard.py            Workspace-scoped dashboard routes
    products.py             Workspace-scoped product and stock movement routes
    qrcode.py               Workspace-scoped QR Code and label routes
  services/
    qrcode_service.py       QR Code and label image generation
    security_service.py     Password hashing and JWT helpers
```

## Environment Variables

Create a local `.env` file from `.env.example`:

```bash
cp .env.example .env
```

Available variables:

```env
DATABASE_URL=sqlite:///./produzzy.db
PRODUZZY_SECRET_KEY=replace-with-a-long-random-secret-key
PRODUZZY_JWT_ALGORITHM=HS256
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES=60
```

Do not commit a real `.env` file or production secrets.

## How to Run Locally

Create and activate a virtual environment:

```bash
python -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Start the API:

```bash
python -m uvicorn app.main:app --reload
```

Open the API docs:

```text
http://127.0.0.1:8000/docs
```

## Authentication

Create a user with `POST /auth/register`:

```json
{
  "name": "Demo User",
  "email": "demo@example.com",
  "password": "strong-password"
}
```

Log in with `POST /auth/login`:

```json
{
  "email": "demo@example.com",
  "password": "strong-password"
}
```

The response returns a bearer token:

```json
{
  "access_token": "jwt-token",
  "token_type": "bearer"
}
```

For Swagger UI, click **Authorize** and use the `/auth/token` flow with:

- `username`: the user email
- `password`: the user password

Then call protected routes from the docs.

## Workspaces

A workspace represents a company, team, or stock context. All products, categories, stock movements, dashboard metrics, QR Codes, and labels are scoped to a workspace.

Main workspace routes:

- `GET /workspaces`
- `POST /workspaces`
- `GET /workspaces/{workspace_id}`
- `PATCH /workspaces/{workspace_id}`

When a user creates a workspace, that user automatically becomes its `owner`.

## Members and Roles

Workspace members have one of these roles:

- `owner`: full control inside the workspace, including workspace updates, member management, and invites.
- `admin`: product/category/stock management, dashboard access, and invites for `employee` or `viewer`.
- `employee`: read access plus stock movements. Employees cannot delete products or manage members.
- `viewer`: read-only access.

Member routes:

- `GET /workspaces/{workspace_id}/members`
- `PATCH /workspaces/{workspace_id}/members/{member_id}`
- `DELETE /workspaces/{workspace_id}/members/{member_id}`

The API protects against removing or demoting the last owner.

## Invites

Email delivery is intentionally not implemented yet. Creating an invite returns a token and symbolic accept URL:

```json
{
  "token": "invite-token",
  "invite_url": "/invites/invite-token/accept"
}
```

Invite routes:

- `POST /workspaces/{workspace_id}/invites`
- `GET /workspaces/{workspace_id}/invites`
- `POST /invites/{token}/accept`
- `POST /workspaces/{workspace_id}/invites/{invite_id}/revoke`

To accept an invite, the logged-in user's email must match the invite email.

## Workspace-Scoped Routes

Products:

- `GET /workspaces/{workspace_id}/products`
- `POST /workspaces/{workspace_id}/products`
- `GET /workspaces/{workspace_id}/products/low-stock`
- `GET /workspaces/{workspace_id}/products/{product_id}`
- `PATCH /workspaces/{workspace_id}/products/{product_id}`
- `DELETE /workspaces/{workspace_id}/products/{product_id}`
- `POST /workspaces/{workspace_id}/products/{product_id}/stock`
- `GET /workspaces/{workspace_id}/products/{product_id}/stock-movements`

Categories:

- `GET /workspaces/{workspace_id}/categories`
- `POST /workspaces/{workspace_id}/categories`
- `GET /workspaces/{workspace_id}/categories/{category_id}`
- `PATCH /workspaces/{workspace_id}/categories/{category_id}`
- `DELETE /workspaces/{workspace_id}/categories/{category_id}`

Dashboard:

- `GET /workspaces/{workspace_id}/dashboard/summary`

QR Codes and labels:

- `GET /workspaces/{workspace_id}/products/{product_id}/qrcode`
- `GET /workspaces/{workspace_id}/products/{product_id}/label`
- `GET /workspaces/{workspace_id}/products/labels-sheet`

## Data Isolation

Before any workspace data is queried, the API validates that the authenticated user is a member of that workspace. Product, category, stock movement, dashboard, QR Code, and label queries are filtered by `workspace_id`.

Legacy global data routes such as `/products`, `/categories`, and `/dashboard/summary` are not exposed as global data endpoints. New clients should use the workspace-scoped routes.

## Pagination

Main list routes support simple pagination:

```text
?page=1&limit=20
```

The maximum `limit` is `100`.

## QR Code and Label Features

Each product can expose a QR Code pointing to its workspace-scoped product detail endpoint. The API can also generate a printable individual product label and an A4 label sheet for the workspace catalog. Images are returned as PNG responses.

## Development Notes

- This project is currently an MVP backend.
- SQLite is used by default for local development.
- Alembic migrations are not configured yet.
- Existing local databases are not recreated automatically.
- The development schema helper adds missing workspace columns and assigns existing products, categories, and stock movements to a `Default Workspace` when an active user exists.
- If no active user exists when old data is present, the helper leaves old data untouched until a proper migration path is available.
- Older SQLite databases may still contain legacy global unique constraints on `products.name` and `categories.name`. The application validates duplicates per workspace, but SQLite may still reject duplicate names across workspaces until Alembic migrations remove the old constraints.
- Automated tests are planned but not included yet.

## Next Steps / Roadmap

- Add automated tests for auth, workspace permissions, invites, data isolation, products, categories, stock movements, dashboard, and image endpoints.
- Add Alembic migrations before production deployment.
- Move production deployments to PostgreSQL.
- Replace symbolic invites with real email delivery.
- Add organization-level billing/subscription metadata if needed.
- Add audit logs for member, invite, product, category, and stock changes.
- Add pagination metadata for larger datasets.
