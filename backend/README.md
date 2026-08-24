# Produzzy API

Produzzy API is an MVP backend for inventory and production control. It is built as a multi-workspace SaaS foundation, so multiple companies, teams, or stock locations can use the same API while keeping their data isolated.

## Features

- JWT authentication with Swagger Authorize support.
- User registration, login, token generation, and current-user lookup.
- Workspaces for company/team/stock isolation.
- Workspace members with roles: `owner`, `admin`, `employee`, and `viewer`.
- Invite flow without email delivery: the API returns an invite token and symbolic accept URL.
- Workspace-scoped product and category management.
- Product soft delete with trash listing and restore support.
- Workspace-scoped stock movements with authenticated user audit fields.
- Basic workspace-scoped audit logs for key mutations.
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
- PostgreSQL as the recommended database
- Alembic for database migrations
- Pydantic
- JWT with `python-jose`
- Password hashing with `passlib` and bcrypt
- `python-dotenv` for local environment variables
- `qrcode` and Pillow for QR Code and label images
- Uvicorn

## Project Structure

```text
alembic/
  env.py                    Alembic environment using app metadata
  versions/                 Database migration files
app/
  config.py                 Environment configuration
  crud.py                   Database operations, workspace rules, and permissions
  database.py               SQLAlchemy engine, session, and legacy SQLite helpers
  dependencies.py           FastAPI dependencies for database and auth
  main.py                   FastAPI application setup
  models.py                 SQLAlchemy models
  schemas.py                Pydantic request and response schemas
  routers/
    auth.py                 Authentication routes
    workspaces.py           Workspace, member, and invite routes
    audit_logs.py           Workspace-scoped audit log routes
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
DATABASE_URL=postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_db
# DATABASE_URL_TEST=postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_test_db
PRODUZZY_ENV=development
PRODUZZY_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000
PRODUZZY_SECRET_KEY=replace-with-a-long-random-secret-key
PRODUZZY_JWT_ALGORITHM=HS256
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES=60
PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_GOOGLE_CLIENT_ID=
PRODUZZY_GOOGLE_CLIENT_SECRET=
```

Do not commit a real `.env` file or production secrets.
Never expose `PRODUZZY_GOOGLE_CLIENT_SECRET` to the frontend. The frontend
only uses the public Google OAuth Client ID through `VITE_GOOGLE_CLIENT_ID`.
Set `PRODUZZY_ENV=production` only in production-like environments. In
production mode, the API refuses to start with the default or a short
`PRODUZZY_SECRET_KEY`, and rejects wildcard or default local CORS origins.

## Google Authentication

Google sign-in uses Google Identity Services with the OAuth authorization code
model in popup mode. The browser requests only these scopes:

```text
openid email profile
```

The frontend sends the authorization code to `POST /auth/google`; the backend
exchanges it with Google, validates the returned ID token, and then issues the
same Produzzy JWT used by email/password login. Google access or refresh tokens
are not stored.

To enable it locally:

1. Create an OAuth Client in Google Cloud Console for a web application.
2. Add your frontend origin to Authorized JavaScript origins, for example
   `http://localhost:5173` or `http://127.0.0.1:5173`.
3. In popup mode, Google uses the calling frontend origin as the `redirect_uri`
   during the backend token exchange. Keep that origin registered in Google
   Cloud and aligned with the value sent by the frontend.
4. Keep the backend `PRODUZZY_ALLOWED_ORIGINS` aligned with the same frontend
   origins.
5. Set `PRODUZZY_GOOGLE_CLIENT_ID` and `PRODUZZY_GOOGLE_CLIENT_SECRET` in the
   backend `.env`.
6. Set `VITE_GOOGLE_CLIENT_ID` in the frontend `.env`.

Do not request Gmail, Drive, contacts, or other Google API scopes unless a real
future feature requires them.

## PostgreSQL Setup

Create a local PostgreSQL user and database:

```bash
sudo -u postgres psql
```

```sql
CREATE USER produzzy_user WITH PASSWORD 'produzzy_password';
CREATE DATABASE produzzy_db OWNER produzzy_user;
CREATE DATABASE produzzy_test_db OWNER produzzy_user;
GRANT ALL PRIVILEGES ON DATABASE produzzy_db TO produzzy_user;
GRANT ALL PRIVILEGES ON DATABASE produzzy_test_db TO produzzy_user;
```

Then set `DATABASE_URL` in `.env`:

```env
DATABASE_URL=postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_db
DATABASE_URL_TEST=postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_test_db
```

SQLite was used during the initial development phase. PostgreSQL + Alembic is now the recommended flow for local development and production-like environments.

## CORS

CORS is configured with `PRODUZZY_ALLOWED_ORIGINS`, a comma-separated list of allowed frontend origins:

```env
PRODUZZY_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000
```

If the variable is missing, the API falls back to the local development origins above. Avoid using `*` in production.
When `PRODUZZY_ENV=production`, `PRODUZZY_ALLOWED_ORIGINS` must contain explicit non-default origins and cannot include `*`.

## Rate Limiting

The API applies an in-memory rate limit to repeated failed attempts for login,
registration, and invite acceptance. Login and registration limits are keyed by
client host and e-mail. Invite acceptance is keyed by client host and the
authenticated user, so repeated failures with different tokens are still
throttled.

The defaults allow 5 failed attempts in 300 seconds:

```env
PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS=300
```

Set an attempt limit to `0` only for controlled local/debug scenarios. For
multi-process or horizontally scaled production deployments, keep this API
limit as a backstop and add a shared edge or proxy-level rate limiter.

## Alembic Migrations

Run migrations before starting the API:

```bash
alembic upgrade head
```

Useful Alembic commands:

```bash
alembic current
alembic history
alembic revision --autogenerate -m "describe change"
```

The initial migration creates the multi-workspace schema:

- `users`
- `workspaces`
- `workspace_members`
- `workspace_invites`
- `categories`
- `products`
- `stock_movements`
- `audit_logs`

Workspace-scoped uniqueness is enforced at the database level:

- active product names are unique per workspace
- category names are unique per workspace
- a user can only be a member of a workspace once
- pending invite emails are unique per workspace

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

Run migrations:

```bash
alembic upgrade head
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
- `GET /workspaces/{workspace_id}/products?status=active|deleted|all`
- `POST /workspaces/{workspace_id}/products`
- `GET /workspaces/{workspace_id}/products/low-stock`
- `GET /workspaces/{workspace_id}/products/{product_id}`
- `GET /workspaces/{workspace_id}/products/{product_id}?include_deleted=true`
- `PATCH /workspaces/{workspace_id}/products/{product_id}`
- `DELETE /workspaces/{workspace_id}/products/{product_id}`
- `POST /workspaces/{workspace_id}/products/{product_id}/restore`
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
- `GET /workspaces/{workspace_id}/products/{product_id}/barcode`
- `GET /workspaces/{workspace_id}/products/{product_id}/label`
- `GET /workspaces/{workspace_id}/products/labels-sheet`

Audit logs:

- `GET /workspaces/{workspace_id}/audit-logs`
- `GET /workspaces/{workspace_id}/audit-logs?action=product.created`
- `GET /workspaces/{workspace_id}/audit-logs?entity_type=product`
- `GET /workspaces/{workspace_id}/audit-logs?user_id={user_id}`

## Data Isolation

Before any workspace data is queried, the API validates that the authenticated user is a member of that workspace. Product, category, stock movement, dashboard, QR Code, and label queries are filtered by `workspace_id`.

Legacy global data routes such as `/products`, `/categories`, and `/dashboard/summary` are not exposed as global data endpoints. New clients should use the workspace-scoped routes.

## Pagination

Main list routes support simple pagination:

```text
?page=1&limit=20
```

The maximum `limit` is `100`.

## Product Soft Delete

Deleting a product does not remove it from the database. `DELETE /workspaces/{workspace_id}/products/{product_id}` marks the product as inactive, stores `deleted_at`, and records `deleted_by_user_id`. Stock movements remain in place for history.

Product lists return active products by default. Use the `status` query parameter to browse the trash or all products:

```text
GET /workspaces/{workspace_id}/products?status=active
GET /workspaces/{workspace_id}/products?status=deleted
GET /workspaces/{workspace_id}/products?status=all
```

Deleted products are hidden from normal detail, QR Code, label, A4 label sheet, low-stock, and dashboard totals. To fetch a deleted product detail directly, use:

```text
GET /workspaces/{workspace_id}/products/{product_id}?include_deleted=true
```

Only `owner` and `admin` members can delete or restore products.

## Restore Product

Restore a deleted product with:

```text
POST /workspaces/{workspace_id}/products/{product_id}/restore
```

Restoring clears `deleted_at` and `deleted_by_user_id` and marks the product active again. Product names are unique among active products in the same workspace, so restoring fails with a `400` response if another active product already uses the same name.

## Audit Logs

The API records basic audit logs for key workspace mutations:

- `workspace.created`
- `workspace.updated`
- `invite.created`
- `invite.accepted`
- `invite.revoked`
- `member.role_updated`
- `member.removed`
- `product.created`
- `product.updated`
- `product.deleted`
- `product.restored`
- `category.created`
- `category.updated`
- `category.deleted`
- `stock.movement_created`

Audit logs are scoped by `workspace_id`. Only `owner` and `admin` members can list them:

```text
GET /workspaces/{workspace_id}/audit-logs?page=1&limit=20
```

Optional filters are available for `action`, `entity_type`, and `user_id`. Audit metadata is intentionally small and does not include passwords, JWTs, password hashes, or invite tokens.

## QR Code and Label Features

Each product can expose a branded QR Code pointing to its workspace-scoped product detail endpoint and a Code128 barcode based on its zero-padded numeric ID. The API can also generate a printable individual product label and an A4 label sheet for the workspace catalog. Images are returned as PNG responses.

## Testing

Tests use `pytest`, `httpx`, and FastAPI's `TestClient`. They are designed to run against a dedicated PostgreSQL test database configured by `DATABASE_URL_TEST`.

Never point `DATABASE_URL_TEST` at your development or production database. The test setup runs migrations on the test database and truncates application tables between tests.

Create the test database:

```sql
CREATE DATABASE produzzy_test_db OWNER produzzy_user;
GRANT ALL PRIVILEGES ON DATABASE produzzy_test_db TO produzzy_user;
```

Set `.env`:

```env
DATABASE_URL_TEST=postgresql://produzzy_user:produzzy_password@localhost:5432/produzzy_test_db
```

Run tests:

```bash
venv/bin/python -m pytest
```

The test suite currently covers auth, workspace ownership, invites, role permissions, workspace isolation, product soft delete/restore, dashboard behavior, and audit log access.

## Development Notes

- This project is currently an MVP backend.
- PostgreSQL + Alembic is the official database flow.
- The API no longer creates tables at startup with `Base.metadata.create_all`.
- Existing SQLite development helpers remain in the codebase only as a legacy fallback and are not called by the main application startup.
- The initial PostgreSQL migration creates workspace-scoped constraints for products and categories.
- SQLite databases created before Alembic may still contain old global unique constraints. Use PostgreSQL migrations for new work.
- Automated tests require `DATABASE_URL_TEST` and must not be run against a development or production database.

## Next Steps / Roadmap

- Add migration tests and schema drift checks.
- Replace symbolic invites with real email delivery.
- Add organization-level billing/subscription metadata if needed.
- Add pagination metadata for larger datasets.
