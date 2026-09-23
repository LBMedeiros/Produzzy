# Produzzy

> Inventory, stock movement, and replenishment management in one collaborative workspace.

Produzzy is a full-stack inventory management SaaS designed to help teams organize products, monitor stock levels, track movements, manage replenishment workflows, and maintain accountability across collaborative workspaces.

The project was inspired by a real operational inventory problem and evolved into a multi-workspace application focused on simplicity, traceability, and efficient stock management.

---

## Overview

Managing inventory becomes increasingly difficult when products, stock movements, replenishment needs, and team responsibilities are tracked separately.

Produzzy brings these operations into a single workflow.

With Produzzy, teams can:

- organize products and categories;
- monitor current and minimum stock levels;
- record stock entries and withdrawals;
- identify low-stock and out-of-stock products;
- manage replenishment workflows;
- track who performed each stock movement;
- collaborate through shared workspaces with custom member titles;
- generate QR Codes, barcodes, and printable product labels;
- scan a product's QR Code or barcode with the camera to jump straight to its stock movement.

---

## Features

### Authentication & Account

- User registration and login with email and password
- JWT-based authentication with protected routes and session handling
- Google OAuth (Sign in with Google)
- Change email and change password from the account settings
- Profile photo upload with an in-app crop/framing editor (stored on Cloudinary)
- Login and registration rate limiting
- Input validation

> Google authentication requires OAuth credentials to be configured through environment variables. See [`DEPLOY.md`](./DEPLOY.md) for the full setup.

### Workspaces & Collaboration

- Create and switch between multiple workspaces
- Fully isolated data between workspaces
- Invite users through individual invitations or shareable invite links
- Member management with role-based permissions (owner, admin, employee, viewer)
- Custom member titles (e.g. "Sócio", "Gerente") — cosmetic labels the owner assigns, independent from access roles
- Workspace deletion with confirmation

### Product Management

- Create and edit products
- Organize products by category (with a trash/restore workflow for categories)
- Search and filter inventory
- Soft delete products with a trash and restore workflow
- Product status derived from inventory levels

### Inventory Control

- Stock entries and withdrawals
- Negative stock prevention
- Minimum stock configuration
- Low-stock and out-of-stock detection
- Persistent stock movement history

### Audit Trail & Activity

Stock movements and workspace actions are recorded with operational context such as:

- responsible user;
- movement type;
- previous quantity, new quantity, and difference;
- reason;
- date and time.

The dashboard surfaces a recent-activity feed (products, categories, replenishments, members, invites, and stock movements), so teams can see who did what and quickly review inventory inconsistencies.

### Replenishment Workflow

Products below their configured minimum stock can enter a replenishment workflow.

Current workflow stages include:

- Replenishment needed
- In progress
- Ready to stock
- Stocked
- Cancelled

The system calculates replenishment needs based on the product's current and minimum quantities, and assignees can be attached to a replenishment.

### QR Codes, Barcodes & Labels

- Individual QR Code and Code 128 barcode generation
- Individual product labels and identification codes
- Batch QR Code and label export (paginated, print-ready sheets)
- Printable previews
- **Camera scanner**: read a product's QR Code or barcode with the device camera to open its stock-movement flow directly

### Interface & UX

- Responsive web interface, tuned for mobile (phone-friendly cards and layouts)
- Light and dark modes with a persistent theme preference and an in-menu toggle
- Responsive sidebar and workspace navigation
- Accessible dropdowns and menus
- Loading, empty, error, and confirmation states
- Subtle interface transitions and motion

---

## Tech Stack

### Frontend

- React 19
- Vite
- JavaScript (JSX)
- React Router (`react-router-dom`)
- TanStack Query (React Query) for server-state
- ZXing (`@zxing/browser`) for QR / barcode scanning
- Plain CSS
- Context API

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- Alembic (migrations)
- python-jose (JWT) · passlib + bcrypt (password hashing)
- Pillow, `qrcode`, and `python-barcode` (QR/barcode/label generation)
- Cloudinary (avatar/media storage)

### Database

- PostgreSQL

### Deployment

- Render (managed PostgreSQL, API web service, and static frontend)

### Development Tools

- Git & GitHub
- Swagger / OpenAPI
- Pytest
- ESLint

---

## Architecture

```text
                    ┌─────────────────────────┐
                    │     React + Vite SPA     │
                    │  React Query · ZXing     │
                    └────────────┬────────────┘
                                 │ REST API (JWT)
                                 ▼
      ┌────────────────────────────────────────────────┐
      │                    FastAPI                       │
      │  Authentication · Workspace-scoped access        │
      │  Business rules · Audit logging                  │
      │  QR / barcode / label generation                 │
      └───────┬─────────────────┬──────────────────┬─────┘
              │                 │                  │
         SQLAlchemy      Cloudinary (media)   Google OAuth
              │                                (sign-in)
              ▼
      ┌─────────────────────┐
      │     PostgreSQL      │
      └─────────────────────┘
```

The application follows a workspace-scoped architecture, ensuring that products, inventory operations, replenishments, and members remain isolated between workspaces.

---

## Project Structure

```text
Produzzy/
├── backend/
│   ├── alembic/                 # database migrations
│   ├── app/
│   │   ├── routers/             # thin HTTP layer (auth, products, stock_movements,
│   │   │                        #   replenishment, categories, workspaces, qrcode,
│   │   │                        #   dashboard, search, audit_logs)
│   │   ├── crud/                # business layer (base, users, products, stock,
│   │   │                        #   categories, workspaces, invites, replenishment,
│   │   │                        #   dashboard, search, audit)
│   │   ├── services/            # security, google_auth, rate_limit,
│   │   │                        #   qrcode, avatar_storage
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── errors.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── tests/
│   ├── .env.example
│   ├── Procfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/          # ui, layout, replenishment, settings, labels
│   │   ├── contexts/            # Auth, Workspace, Theme
│   │   ├── pages/
│   │   ├── services/            # API layer per domain
│   │   ├── lib/                 # api client, formatters, replenishment helpers
│   │   └── styles/
│   ├── .env.example
│   └── package.json
│
├── render.yaml                  # Render Blueprint
├── DEPLOY.md                    # deployment checklist
├── .gitignore
└── README.md
```

---

## Running Locally

### Requirements

Make sure you have installed:

- Python 3
- Node.js
- npm
- PostgreSQL
- Git

---

### 1. Clone the repository

```bash
git clone https://github.com/LBMedeiros/Produzzy.git
cd Produzzy
```

---

### 2. Backend setup

Enter the backend directory:

```bash
cd backend
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate it on Linux/macOS:

```bash
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Create your local environment file:

```bash
cp .env.example .env
```

Configure your PostgreSQL connection and application secrets in `.env`.

Run database migrations:

```bash
alembic upgrade head
```

Start the API:

```bash
uvicorn app.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

---

### 3. Frontend setup

Open another terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the local environment file:

```bash
cp .env.example .env.local
```

Start the development server:

```bash
npm run dev
```

The frontend will normally be available at:

```text
http://localhost:5173
```

---

## Environment Variables

### Backend

Example (see [`backend/.env.example`](./backend/.env.example) for the full list):

```env
DATABASE_URL=postgresql://user:password@localhost:5432/produzzy

PRODUZZY_ENV=development
PRODUZZY_ALLOWED_ORIGINS=http://localhost:5173

PRODUZZY_SECRET_KEY=replace-with-a-long-random-secret-key
PRODUZZY_JWT_ALGORITHM=HS256
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES=60

PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS=300

# Optional — Sign in with Google
PRODUZZY_GOOGLE_CLIENT_ID=
PRODUZZY_GOOGLE_CLIENT_SECRET=

# Optional — profile photo upload (all three required together)
PRODUZZY_CLOUDINARY_CLOUD_NAME=
PRODUZZY_CLOUDINARY_API_KEY=
PRODUZZY_CLOUDINARY_API_SECRET=

# Optional — PostgreSQL connection pool tuning
# DB_POOL_RECYCLE_SECONDS=1800
# DB_POOL_SIZE=5
# DB_MAX_OVERFLOW=10
```

### Frontend

```env
VITE_API_URL=http://127.0.0.1:8000
VITE_GOOGLE_CLIENT_ID=
```

Never commit real secrets, database credentials, access tokens, or OAuth client secrets.

---

## Database Migrations

Produzzy uses Alembic for database schema migrations.

Apply all migrations:

```bash
alembic upgrade head
```

Check the current migration:

```bash
alembic current
```

Check the latest available migration:

```bash
alembic heads
```

---

## Quality Checks

### Frontend

Run ESLint:

```bash
npm run lint
```

Create a production build:

```bash
npm run build
```

### Backend

Run the test suite (integration tests against a real PostgreSQL database; requires `DATABASE_URL_TEST`):

```bash
python -m pytest
```

Compile the backend modules:

```bash
python -m compileall app alembic tests
```

---

## Deployment

Produzzy is deployed on **Render** using the [`render.yaml`](./render.yaml) Blueprint, which provisions a managed PostgreSQL database, the FastAPI API, and the static React frontend.

- Migrations run automatically as a pre-deploy step (`alembic upgrade head`).
- The API exposes `/health` and `/ready` probes.
- The frontend is served as an SPA with a `/* → /index.html` rewrite.

The full operational checklist (required environment variables, Google OAuth, Cloudinary, and post-deploy smoke tests) lives in [`DEPLOY.md`](./DEPLOY.md).

---

## Screenshots

> Screenshots and a live demo will be added as the public release is finalized.

Suggested showcase:

- Dashboard
- Inventory
- Replenishment workflow
- QR Code, barcode & labels
- Camera scanner
- Workspace settings
- Dark mode
- Mobile experience

---

## Current Status

**Produzzy is under active development and deployed to production.**

The core SaaS architecture and inventory workflow are implemented, and the app is live on Render. Current work focuses on:

- end-to-end quality assurance;
- permission and workspace isolation testing;
- concurrent inventory operation testing;
- expanded automated test coverage;
- production monitoring and backups;
- account recovery flows.

---

## Roadmap

- [x] Email/password authentication
- [x] JWT authentication
- [x] Google OAuth
- [x] Multi-workspace architecture
- [x] Workspace invitations (individual and link-based)
- [x] Role-based access
- [x] Custom member titles
- [x] Product and category management
- [x] Stock movements
- [x] Negative stock validation
- [x] Low-stock monitoring
- [x] Replenishment workflow
- [x] Activity & stock movement audit trail
- [x] Product soft delete
- [x] QR Code, barcode, and label generation
- [x] Camera QR / barcode scanner
- [x] Profile photo upload with crop editor
- [x] Light and dark themes
- [x] Mobile-responsive interface
- [x] Production deployment (Render)
- [ ] Complete end-to-end QA
- [ ] Expanded automated test coverage
- [ ] Production monitoring and backups
- [ ] Password recovery and email verification

---

## Why Produzzy?

Produzzy started from a real inventory and replenishment challenge involving a large number of products that needed to be organized, located, monitored, and replenished efficiently.

Instead of building another tutorial CRUD application, the goal of Produzzy is to explore how a real operational problem can evolve into a structured full-stack product with authentication, multi-user collaboration, inventory rules, auditability, and scalable software architecture.

---

## Author

**Lucas Medeiros**

Software Engineering Student & Full Stack Developer

- GitHub: [LBMedeiros](https://github.com/LBMedeiros)
- LinkedIn: [linkedin.com/in/lbmedeiros](https://linkedin.com/in/lbmedeiros)

---

Built with React, FastAPI and PostgreSQL.
