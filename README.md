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
- hand off replenishment work through a per-request chat;
- generate QR Codes, barcodes, and printable product labels;
- scan a product's QR Code or barcode with the camera to jump straight to its stock movement;
- see what needs attention at a glance on a dashboard with a 7-day movement chart.

---

## Features

### Authentication & Account

- User registration and login with email and password (accounts are active right after sign-up, with automatic login)
- Password policy enforced on both backend and frontend: 8+ characters with at least one number and one special character, with a live checklist while typing
- JWT-based authentication with protected routes and session handling
- "Remember me" keeps the session for 30 days (configurable); otherwise the session ends with the browser
- Changing the password signs out every other session (tokens carry a password fingerprint)
- Google OAuth (Sign in with Google)
- Change email and change password from the account settings
- Password recovery ("forgot password") via a single-use e-mail reset link
- Optional backup recovery e-mail (confirmed by link) that also receives the reset link, with a Pending/Confirmed status and a "resend confirmation" action
- Profile photo upload with an in-app crop/framing editor (stored on Cloudinary)
- Login, registration, forgot-password and invite-acceptance rate limiting, keyed on the real client IP behind the Render proxy
- Input validation

> Google authentication requires OAuth credentials, and password recovery requires SMTP e-mail settings, both configured through environment variables. See [`DEPLOY.md`](./DEPLOY.md) for the full setup.

### Privacy & LGPD

- Public Terms of Use (`/termos`) and Privacy Policy (`/privacidade`) pages
- "Download my data": a formatted PDF export of the account, workspaces, per-workspace summary, and activity history (generated client-side with jsPDF)
- Account deletion from Settings (personal data is anonymized and the account deactivated)

### Workspaces & Collaboration

- Create and switch between multiple workspaces
- Fully isolated data between workspaces
- Invite users through individual invitations or shareable invite links
- Member management with role-based permissions (owner, admin, employee, viewer)
- Custom member titles (e.g. "Sócio", "Gerente") — cosmetic labels the owner assigns, independent from access roles
- Workspace deletion with confirmation

### Dashboard

- Greeting with summary tiles (active products, below minimum, out of stock, movements today)
- "Needs attention" list of low and out-of-stock products, linked to their replenishment
- Stalled replenishments (no update for 3+ days) and replenishments ready to stock
- 7-day chart of stock entries and exits (in the user's time zone)
- Readable recent-activity feed with the member's photo and name

### Product Management

- Create and edit products
- Organize products by category (with a trash/restore workflow for categories)
- Search and filter inventory, with filter chips and counts (All, Below minimum, Out of stock, History, Trash)
- Paginated product lists, with no cap on how many products a workspace can have
- Stock level bar per product and its last movement ("Lucas · exit of 6 · 1 h ago")
- Soft delete products with a trash and restore workflow
- Product and category names are unique per workspace, case-insensitively (e.g. "Café" and "café" are the same name)
- Product status derived from inventory levels
- Global search across the workspace

### Inventory Control

- Stock entries and withdrawals
- Negative stock prevention
- Quantities capped at 1,000,000,000 (clean validation error instead of a database overflow)
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

The system calculates replenishment needs based on the product's current and minimum quantities.

- Three-column board (Replenishment needed, In progress, Ready to stock), each column scrolling on its own, with stocked and cancelled requests in a paginated history
- Product search that filters every column and the history (accent and case insensitive)
- Each card shows the stock level, the assignee and how long the request has been open or stalled, plus a single next action
- On phones, one stage at a time through chips
- Confirming a new replenishment assigns its creator and starts it directly as *In progress*
- Additional assignees can be attached to a replenishment
- **Handoff chat**: each request has its own message thread, so assignees can leave notes on where they stopped; everyone with board access can read it
- **Retention**: cancelled requests are removed after 7 days, and the chat of finalized requests after 30 days (cleanup runs lazily, at most once a day)

### QR Codes, Barcodes & Labels

- One label per product with both a QR Code (Produzzy logo in the center) and a Code 128 barcode
- Product picker with search, select all and pagination, plus a copies counter
- Live preview of the real A4 sheet generated by the API
- Download as PDF or print directly (up to 120 labels per request)
- **Camera scanner**: read a product's QR Code or barcode with the device camera to open its stock-movement flow directly

### Interface & UX

- Redesigned interface (spec in [`docs/redesign/`](./docs/redesign/)): one visual system for colors, status badges and stock levels
- Desktop: compact icon sidebar; phones: one-line header, bottom tab bar and a "+" quick-action button
- Login landing page with the sign-in card centered and a product showcase revealed as you scroll
- Light and dark modes with a persistent theme preference and an in-menu toggle
- Team popover with member photos and pending invites listed separately
- Accessibility: AA text contrast in both themes, visible keyboard focus, and form validation messages in Portuguese
- Loading, empty, error, and confirmation states
- Subtle interface transitions and motion (respects "reduce motion")

---

## Tech Stack

### Frontend

- React 19
- Vite
- JavaScript (JSX)
- React Router (`react-router-dom`)
- TanStack Query (React Query) for server-state
- ZXing (`@zxing/browser`) for QR / barcode scanning
- jsPDF for the personal-data PDF export
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
- SMTP (provider-agnostic) for password-reset and recovery e-mails

### Database

- PostgreSQL (hosted on Neon in production)

### Deployment

- Render (API web service and static frontend) + Neon (managed PostgreSQL)

### Development Tools

- Git & GitHub
- Swagger / OpenAPI
- Pytest
- ESLint
- GitHub Actions (CI)

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
              │          SMTP (e-mails)        (sign-in)
              ▼
      ┌─────────────────────┐
      │ PostgreSQL (Neon)   │
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
│   │   │                        #   qrcode, avatar_storage, email
│   │   ├── assets/              # brand icon used on QR codes/labels
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
│   │   ├── components/          # ui, layout, dashboard, replenishment, settings,
│   │   │                        #   labels, auth, legal
│   │   ├── contexts/            # Auth, Workspace, Theme
│   │   ├── pages/               # dashboard, stock, production, labels, settings,
│   │   │                        #   auth flows, terms/privacy, invite acceptance
│   │   ├── services/            # API layer per domain
│   │   ├── lib/                 # api client, formatters, pagination, activity,
│   │   │                        #   replenishment helpers, password policy,
│   │   │                        #   PDF data export, login motion
│   │   └── styles/
│   ├── .env.example
│   └── package.json
│
├── docs/redesign/               # interface redesign spec and prototype
├── .github/workflows/ci.yml     # CI: lint, build and backend tests
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
# Dedicated test database (must differ from DATABASE_URL)
# DATABASE_URL_TEST=postgresql://user:password@localhost:5432/produzzy_test

PRODUZZY_ENV=development
PRODUZZY_API_VERSION=
PRODUZZY_ALLOWED_ORIGINS=http://localhost:5173

PRODUZZY_SECRET_KEY=replace-with-a-long-random-secret-key
PRODUZZY_JWT_ALGORITHM=HS256
PRODUZZY_ACCESS_TOKEN_EXPIRE_MINUTES=60
# Session length when "remember me" is checked
PRODUZZY_REMEMBER_ME_EXPIRE_DAYS=30

PRODUZZY_LOGIN_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_LOGIN_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_REGISTER_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_REGISTER_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_INVITE_ACCEPT_RATE_LIMIT_WINDOW_SECONDS=300
PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_ATTEMPTS=5
PRODUZZY_FORGOT_PASSWORD_RATE_LIMIT_WINDOW_SECONDS=900

# Lifetime of e-mailed links, in minutes
PRODUZZY_PASSWORD_RESET_TOKEN_EXPIRE_MINUTES=30
# PRODUZZY_EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES=

# Optional — Sign in with Google
PRODUZZY_GOOGLE_CLIENT_ID=
PRODUZZY_GOOGLE_CLIENT_SECRET=

# Optional — profile photo upload (all three required together)
PRODUZZY_CLOUDINARY_CLOUD_NAME=
PRODUZZY_CLOUDINARY_API_KEY=
PRODUZZY_CLOUDINARY_API_SECRET=

# Optional — SMTP e-mail, required for password recovery and recovery-e-mail confirmation
PRODUZZY_SMTP_HOST=
PRODUZZY_SMTP_PORT=587
PRODUZZY_SMTP_USER=
PRODUZZY_SMTP_PASSWORD=
PRODUZZY_SMTP_FROM=
PRODUZZY_SMTP_FROM_NAME=Produzzy
PRODUZZY_SMTP_USE_TLS=true
# Public frontend URL used in the reset link (defaults to first allowed origin)
PRODUZZY_APP_BASE_URL=

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

### Continuous Integration

Every pull request runs [GitHub Actions](./.github/workflows/ci.yml): the frontend lint and build, and the backend test suite against a PostgreSQL 16 service.

---

## Deployment

Produzzy is deployed on **Render** using the [`render.yaml`](./render.yaml) Blueprint, which provisions the FastAPI API and the static React frontend. The database is an external managed PostgreSQL on **Neon** (pooled connection string with `sslmode=require` in `DATABASE_URL`); the Blueprint keeps a commented-out Render Postgres block as an alternative.

- Migrations run automatically as a pre-deploy step (`alembic upgrade head`).
- The API exposes `/health` and `/ready` probes.
- The frontend is served as an SPA with a `/* → /index.html` rewrite.

The full operational checklist (required environment variables, Neon, Google OAuth, Cloudinary, SMTP, and post-deploy smoke tests) lives in [`DEPLOY.md`](./DEPLOY.md).

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

The core SaaS architecture and inventory workflow are implemented, the full interface redesign has shipped, and the app is live on Render. Current work focuses on:

- end-to-end quality assurance;
- permission and workspace isolation testing;
- concurrent inventory operation testing;
- expanded automated test coverage;
- production monitoring and backups.

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
- [x] Replenishment handoff chat and data retention
- [x] Activity & stock movement audit trail
- [x] Product soft delete
- [x] QR Code, barcode, and label generation
- [x] Camera QR / barcode scanner
- [x] Profile photo upload with crop editor
- [x] Light and dark themes
- [x] Mobile-responsive interface
- [x] Password recovery and backup recovery e-mail
- [x] Password strength policy
- [x] Terms of Use, Privacy Policy, and LGPD data rights (PDF export, account deletion)
- [x] Production deployment (Render + Neon)
- [x] Continuous integration (GitHub Actions)
- [x] Dashboard with 7-day movement chart
- [x] Full interface redesign (desktop and mobile)
- [x] A4 label sheets with PDF download
- [ ] Complete end-to-end QA
- [ ] Expanded automated test coverage
- [ ] Production monitoring and backups

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
