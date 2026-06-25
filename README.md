# Produzzy API

Produzzy API is an MVP backend for inventory and production control. It provides authentication, product and category management, stock movement tracking, dashboard metrics, QR Code generation, and printable product labels.

## Features

- JWT authentication with Swagger Authorize support.
- User registration, login, token generation, and current-user lookup.
- Product CRUD with protected write operations.
- Category CRUD with protected write operations.
- Stock movement creation for entries, exits, and adjustments.
- Stock movement audit data with the authenticated user when available.
- Low-stock product listing.
- Dashboard summary for inventory totals.
- Product QR Code generation.
- Individual product label generation.
- A4 label sheet generation for registered products.

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
  crud.py                   Database operations and business rules
  database.py               SQLAlchemy engine, session, and local schema helpers
  dependencies.py           FastAPI dependencies for database and auth
  main.py                   FastAPI application setup
  models.py                 SQLAlchemy models
  schemas.py                Pydantic request and response schemas
  routers/
    auth.py                 Authentication routes
    categories.py           Category routes
    dashboard.py            Dashboard routes
    products.py             Product and stock movement routes
    qrcode.py               QR Code and label routes
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

SQLite remains the default development database. The application uses `Base.metadata.create_all(bind=engine)` for local schema creation and includes a small idempotent SQLite helper for the current development schema.

## How to Create a User

Use `POST /auth/register` with a JSON body:

```json
{
  "name": "Demo User",
  "email": "demo@example.com",
  "password": "strong-password"
}
```

## How to Authenticate

Use `POST /auth/login` with JSON credentials:

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

## Main API Modules

- `GET /` and `GET /health`: application status.
- `/auth`: user registration, login, Swagger token, and current user.
- `/products`: product listing, product management, and stock movements.
- `/categories`: category listing and management.
- `/dashboard/summary`: inventory summary metrics.
- `/products/{product_id}/qrcode`: product QR Code image.
- `/products/{product_id}/label`: individual product label image.
- `/products/labels-sheet`: A4 sheet with product labels.

## Protected Routes

Write operations require a valid bearer token:

- `POST /products`
- `PATCH /products/{product_id}`
- `DELETE /products/{product_id}`
- `POST /products/{product_id}/stock`
- `POST /categories`
- `PATCH /categories/{category_id}`
- `DELETE /categories/{category_id}`

Dashboard summary and `/auth/me` also require authentication.

Public read routes remain available without authentication, including product listing, product details, low-stock listing, category listing, QR Codes, labels, and the root health endpoints.

## QR Code and Label Features

Each product can expose a QR Code that points to its product detail endpoint. The API can also generate a printable individual product label and an A4 label sheet for the current product catalog. Images are returned as PNG responses.

## Development Notes

- This project is currently an MVP backend.
- SQLite is used by default for local development.
- Alembic migrations are not configured yet.
- Existing local databases are not recreated automatically.
- Stock movements may have `user_id`, `user_name`, and `user_email` when created by an authenticated user. Older movements can return `null` user fields.
- Automated tests are planned but not included yet.

## Next Steps / Roadmap

- Add automated tests for auth, products, categories, stock movements, dashboard, and image endpoints.
- Add Alembic migrations before production deployment.
- Add role-based authorization if the product needs admin/operator permissions.
- Add pagination and filtering for larger product and movement datasets.
- Add production database configuration when moving beyond local development.
