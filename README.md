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
- track who performed stock movements;
- collaborate through shared workspaces;
- generate QR Codes and printable product labels.

---

## Features

### Authentication

- User registration and login with email and password
- JWT-based authentication
- Protected routes
- Session handling
- Google OAuth support
- Login rate limiting
- Input validation

> Google authentication requires OAuth credentials to be configured through environment variables.

### Workspaces

- Create multiple workspaces
- Isolated data between workspaces
- Workspace switching
- Invite users through invitation links
- Member management
- Role-based permissions
- Workspace deletion with confirmation

### Product Management

- Create products
- Edit product information
- Organize products by category
- Search and filter inventory
- Soft delete products
- Trash and restore workflow
- Product status based on inventory levels

### Inventory Control

- Stock entries
- Stock withdrawals
- Negative stock prevention
- Minimum stock configuration
- Low-stock detection
- Out-of-stock detection
- Persistent stock movement history

### Audit Trail

Stock movements include operational information such as:

- responsible user;
- movement type;
- previous quantity;
- new quantity;
- quantity difference;
- reason;
- date and time.

This allows teams to identify who performed a stock operation when reviewing inventory inconsistencies.

### Replenishment Workflow

Products below their configured minimum stock can enter a replenishment workflow.

Current workflow stages include:

- Replenishment needed
- In progress
- Ready to stock
- Stocked
- Cancelled

The system calculates replenishment needs based on the product's current and minimum quantities.

### QR Codes & Labels

- Individual QR Code generation
- Individual product labels
- Product identification codes
- Batch QR Code export
- Batch label export
- Printable previews

### Interface

- Responsive web interface
- Light mode
- Dark mode
- Persistent theme preference
- Responsive sidebar
- Workspace navigation
- Accessible dropdowns and menus
- Loading, empty, error, and confirmation states
- Subtle interface transitions and motion

---

## Tech Stack

### Frontend

- React
- Vite
- JavaScript
- React Router
- CSS
- Context API

### Backend

- Python
- FastAPI
- SQLAlchemy
- Pydantic
- JWT authentication
- Alembic

### Database

- PostgreSQL

### Authentication

- Email & password
- JWT
- Google Identity / OAuth

### Development Tools

- Git
- GitHub
- Swagger / OpenAPI
- Pytest
- ESLint

---

## Architecture

```text
                       ┌─────────────────────┐
                       │      React App      │
                       │        Vite         │
                       └──────────┬──────────┘
                                  │
                                  │ REST API
                                  ▼
                       ┌─────────────────────┐
                       │       FastAPI       │
                       │ Authentication      │
                       │ Business Rules      │
                       │ Workspace Access    │
                       └──────────┬──────────┘
                                  │
                              SQLAlchemy
                                  │
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
│   ├── alembic/
│   ├── app/
│   │   ├── routers/
│   │   ├── services/
│   │   ├── config.py
│   │   ├── crud.py
│   │   ├── database.py
│   │   ├── dependencies.py
│   │   ├── main.py
│   │   ├── models.py
│   │   └── schemas.py
│   ├── tests/
│   ├── .env.example
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── contexts/
│   │   ├── pages/
│   │   ├── services/
│   │   └── styles/
│   ├── .env.example
│   └── package.json
│
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
git clone git@github.com:LBMedeiros/Produzzy.git
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

Example:

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

PRODUZZY_GOOGLE_CLIENT_ID=
PRODUZZY_GOOGLE_CLIENT_SECRET=
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

Run the test suite:

```bash
python -m pytest
```

Compile the backend modules:

```bash
python -m compileall app alembic tests
```

---

## Screenshots

> Screenshots and live demo will be added as the public release is finalized.

Suggested showcase:

- Dashboard
- Inventory
- Replenishment workflow
- QR Code & Labels
- Workspace settings
- Dark mode
- Mobile experience

---

## Current Status

**Produzzy is under active development.**

The core SaaS architecture and inventory workflow are already implemented. The current development stage is focused on:

- end-to-end quality assurance;
- permission and workspace isolation testing;
- concurrent inventory operation testing;
- deployment;
- production configuration;
- mobile UX improvements;
- automated test coverage.

---

## Roadmap

- [x] Email/password authentication
- [x] JWT authentication
- [x] Multi-workspace architecture
- [x] Workspace invitations
- [x] Role-based access
- [x] Product and category management
- [x] Stock movements
- [x] Negative stock validation
- [x] Low-stock monitoring
- [x] Replenishment workflow
- [x] Stock movement audit trail
- [x] Product soft delete
- [x] QR Code generation
- [x] Product label generation
- [x] Light and Dark themes
- [ ] Complete end-to-end QA
- [ ] Production deployment
- [ ] Expanded automated test coverage
- [ ] Dedicated mobile UX
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
