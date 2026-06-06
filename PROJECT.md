# LeadPulse CRM — Project Documentation

> **Lead Management & CRM Lifecycle Platform**
> Version 1.0.0 | June 2026

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Project Name Rationale](#2-project-name-rationale)
3. [Tech Stack Decisions](#3-tech-stack-decisions)
   - 3.1 [Backend Framework Analysis](#31-backend-framework-analysis)
   - 3.2 [Frontend UI Library Analysis](#32-frontend-ui-library-analysis)
   - 3.3 [Data Grid Analysis](#33-data-grid-analysis)
   - 3.4 [Final Stack Summary](#34-final-stack-summary)
4. [System Architecture](#4-system-architecture)
5. [Folder Structure](#5-folder-structure)
6. [Database Schema](#6-database-schema)
7. [RBAC — Role-Based Access Control](#7-rbac--role-based-access-control)
8. [CRM Lead Lifecycle](#8-crm-lead-lifecycle)
9. [API Reference](#9-api-reference)
10. [Environment Variables](#10-environment-variables)
11. [Setup & Run Instructions](#11-setup--run-instructions)
12. [Development Roadmap](#12-development-roadmap)

---

## 1. Project Overview

**LeadPulse CRM** is a full-stack Lead Management and CRM lifecycle platform designed to help sales teams capture, track, and close leads efficiently.

### Core Features
- **Lead Management** — Create, edit, assign, and track leads through the full sales lifecycle
- **Pipeline View** — Kanban-style drag-and-drop board organized by lead stage
- **Activity Tracking** — Log calls, emails, meetings, tasks and notes against each lead
- **Role-Based Access Control** — Four roles with fine-grained permissions
- **Analytics Dashboard** — KPI cards, pipeline charts, win rate tracking
- **User Management** — Admin-only user creation and role assignment

### Business Requirements (from CRM_Lead_Automation_Workflow.docx)
- Automated lead assignment workflows
- Stage-based lifecycle tracking (New → Won/Lost)
- Role-based admin panel visibility
- Lead activity timeline per record
- Pipeline value and conversion reporting

---

## 2. Project Name Rationale

**LeadPulse CRM** was chosen because:

| Word | Meaning |
|------|---------|
| **Lead** | Directly references the core entity being managed |
| **Pulse** | Implies real-time monitoring, vitality, and a continuous heartbeat of the pipeline — the system "takes the pulse" of your sales |
| **CRM** | Clear category identifier for discoverability |

Alternative names considered: LeadNexus, PipelineForge, SalesNexus, LeadFlow Pro.

---

## 3. Tech Stack Decisions

### 3.1 Backend Framework Analysis

| Criterion | FastAPI ✅ | Django + DRF | Flask |
|-----------|-----------|--------------|-------|
| **Performance** | ⭐⭐⭐ Async-native, 3× faster | ⭐⭐ Sync-first | ⭐⭐ Lightweight |
| **Built-in Admin Panel** | ✗ (frontend is the admin) | ✓ Django Admin | ✗ |
| **JWT / RBAC** | ✓ python-jose + custom | ✓ Django permissions | ✓ Flask-Principal |
| **ORM** | SQLAlchemy 2.0 (explicit) | Django ORM (magic) | SQLAlchemy |
| **Async / WebSocket** | ✓ Native (Starlette) | Partial (Django Channels) | Partial |
| **Data Validation** | ✓ Pydantic v2 (strict, fast) | Serializers (verbose) | Marshmallow |
| **Auto API Docs** | ✓ Swagger + ReDoc built-in | DRF Browsable API | Manual |
| **DB Migrations** | Alembic (explicit) | Django Migrations (built-in) | Alembic |
| **Learning Curve** | Moderate | Steep | Easy |
| **Ecosystem Age** | 5 years | 20 years | 18 years |

**Decision: FastAPI**

Reasons:
- API-first architecture aligns with a separate Next.js frontend (no server-side rendering needed from backend)
- Native async enables WebSocket support for real-time lead updates (Phase 2)
- Pydantic v2 provides automatic request validation and OpenAPI documentation
- SQLAlchemy 2.0 with Alembic gives precise schema control and migration history
- Smaller memory footprint → lower hosting costs

---

### 3.2 Frontend UI Library Analysis

| Library | License | Bundle | Data Grid | Next.js 14 App Router | Tailwind-Native | Customization |
|---------|---------|--------|-----------|----------------------|-----------------|---------------|
| **Shadcn/UI + TailwindCSS** ✅ | MIT | ~50KB | Via TanStack Table | ⭐⭐⭐ Native | ⭐⭐⭐ Yes | ⭐⭐⭐ Full |
| MUI + DataGrid Community | MIT | ~180KB | Built-in DataGrid | ⭐⭐ Good | ✗ CSS-in-JS | ⭐⭐ Theming |
| Ant Design (antd) | MIT | ~200KB | Built-in Table | ⭐⭐ Good | ✗ LESS/CSS | ⭐⭐ Design tokens |
| Mantine + DataTable | MIT | ~150KB | Mantine DataTable | ⭐⭐ Good | ✗ CSS modules | ⭐⭐ Props |
| Tremor | Apache 2.0 | ~80KB | No grid | ⭐⭐ Good | ✓ Yes | ⭐ Limited |
| Chakra UI | MIT | ~160KB | No grid | ⭐⭐ Good | ✗ Emotion | ⭐⭐ Theme |

**Decision: Shadcn/UI + TailwindCSS**

Reasons:
- **Copy model** — components are copied into your repo, giving 100% ownership and no package dependency lock-in
- **Zero-cost tree-shaking** — install only what you need, no bloat
- **Next.js 14 App Router** is the primary supported environment
- **Accessibility** — built on Base UI (Radix UI successor) with full ARIA support
- **Tailwind-native** — consistent with the utility-first approach throughout the codebase
- **Active ecosystem** — 60k+ GitHub stars, shadcn components used by Vercel, Linear, etc.

---

### 3.3 Data Grid Analysis

| Library | License | Free Features | Server Pagination | Virtual Scroll | Bundle |
|---------|---------|--------------|-------------------|----------------|--------|
| **TanStack Table v8** ✅ | MIT | All features free | ✓ Controlled | ✓ Via TanStack Virtual | ~10KB |
| AG Grid Community | MIT | Limited (no virtualization) | ✓ | ✗ Community | ~300KB |
| MUI DataGrid Community | MIT | No row grouping, no Excel export | ✓ | ✗ Community | +60KB |
| React Table (v6) | MIT | Legacy, deprecated | ✓ | ✗ | ~15KB |

**Decision: TanStack Table v8 (headless) + Shadcn Table component**

Reasons:
- **Headless** — pure logic, zero DOM opinion. Styled with Shadcn/Tailwind for full design control
- **Feature-complete in free tier** — sorting, filtering, pagination, column visibility, row selection, grouping all included
- **TypeScript-first** — generic column definitions with full type inference
- **1.6 billion downloads** — most used data grid engine in the world
- **Server-side pagination** — controlled mode enables API-driven pagination for large datasets

---

### 3.4 Final Stack Summary

```
┌─────────────────────────────────────────────────────────────────┐
│                      LeadPulse CRM Stack                        │
├──────────────────────────┬──────────────────────────────────────┤
│ Layer                    │ Technology                           │
├──────────────────────────┼──────────────────────────────────────┤
│ Frontend Framework       │ Next.js 14 (App Router)             │
│ UI Component Library     │ Shadcn/UI (Base UI + Radix)         │
│ Styling                  │ TailwindCSS 3                        │
│ Data Grid Engine         │ TanStack Table v8                    │
│ Server State             │ TanStack Query v5 (React Query)      │
│ Client State             │ Zustand v4                           │
│ Form Validation          │ React Hook Form + Zod                │
│ Charts                   │ Recharts                             │
│ Kanban DnD               │ @hello-pangea/dnd                    │
│ HTTP Client              │ Axios (with JWT interceptors)        │
│ Notifications            │ Sonner                               │
├──────────────────────────┼──────────────────────────────────────┤
│ Backend Framework        │ FastAPI 0.115                        │
│ Language                 │ Python 3.11+                         │
│ ORM                      │ SQLAlchemy 2.0 (mapped columns)      │
│ Database Migrations      │ Alembic                              │
│ Authentication           │ JWT (python-jose) + bcrypt (passlib) │
│ Data Validation          │ Pydantic v2                          │
│ Database (dev)           │ SQLite (WAL mode)                    │
│ Database (prod)          │ PostgreSQL 15+                       │
│ ASGI Server              │ Uvicorn                              │
└──────────────────────────┴──────────────────────────────────────┘
```

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          Client Browser                              │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTPS
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              leadpulse-frontend (Next.js 14 / port 3000)            │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────────────────┐  │
│  │  Auth Pages  │  │ Dashboard    │  │ Protected Routes           │  │
│  │  /login      │  │ /dashboard   │  │ /leads /pipeline           │  │
│  └─────────────┘  │ /analytics   │  │ /activities /users         │  │
│                   └──────────────┘  └───────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ Zustand Store (authStore) ← JWT tokens + user profile        │   │
│  │ TanStack Query ← API cache + optimistic updates              │   │
│  │ Axios client ← /api/v1/* with Bearer token + auto-refresh    │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP REST  (JSON)
                               │ Bearer Token
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│              leadpulse-backend (FastAPI / port 8000)                 │
│                                                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │  /api/v1/    │  │  JWT Auth    │  │  RBAC Middleware          │  │
│  │  auth        │  │  (python-    │  │  (role-level permission   │  │
│  │  users       │  │   jose)      │  │   checks per endpoint)   │  │
│  │  leads       │  │              │  │                          │  │
│  │  analytics   │  └──────────────┘  └──────────────────────────┘  │
│  └──────────────┘                                                    │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ SQLAlchemy 2.0 ORM (mapped columns, relationships)           │   │
│  │ Alembic (schema migrations, version controlled)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    Database (SQLite / PostgreSQL)                     │
│                                                                      │
│   ┌──────────┐     ┌──────────────┐     ┌──────────────────────┐   │
│   │  users   │────▶│    leads     │────▶│      activities      │   │
│   └──────────┘     └──────────────┘     └──────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. Folder Structure

### Backend — `leadpulse-backend/`

```
leadpulse-backend/
├── app/
│   ├── __init__.py
│   ├── main.py               ← FastAPI app factory, CORS, lifespan, seed
│   ├── config.py             ← Pydantic Settings (reads .env)
│   ├── database.py           ← SQLAlchemy engine + session factory
│   │
│   ├── models/
│   │   ├── __init__.py       ← Re-exports all models
│   │   ├── user.py           ← User model + UserRole enum
│   │   ├── lead.py           ← Lead model + LeadStage/Priority/Source enums
│   │   └── activity.py       ← Activity model + ActivityType enum
│   │
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── auth.py           ← Token, LoginRequest, RefreshRequest
│   │   ├── user.py           ← UserCreate, UserRead, UserUpdate
│   │   ├── lead.py           ← LeadCreate, LeadRead, LeadUpdate, LeadListResponse
│   │   └── activity.py       ← ActivityCreate, ActivityRead
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── deps.py           ← get_current_user, get_current_active_user
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── router.py     ← Combines all sub-routers under /api/v1
│   │       ├── auth.py       ← POST /login, POST /refresh, GET /me
│   │       ├── users.py      ← CRUD /users
│   │       ├── leads.py      ← CRUD /leads + /leads/{id}/activities
│   │       └── analytics.py  ← GET /analytics/dashboard, /analytics/pipeline
│   │
│   └── core/
│       ├── __init__.py
│       ├── security.py       ← JWT encode/decode, bcrypt hash/verify
│       └── rbac.py           ← Role hierarchy, permission helpers
│
├── alembic/
│   ├── env.py                ← Alembic env, imports app models
│   └── versions/
│       └── 0fc932bde3bc_initial_schema.py
│
├── tests/
├── alembic.ini
├── requirements.txt
├── .env                      ← (git-ignored, copied from .env.example)
└── .env.example
```

### Frontend — `leadpulse-frontend/`

```
leadpulse-frontend/
├── app/
│   ├── layout.tsx            ← Root layout: fonts, Providers, Toaster
│   ├── page.tsx              ← redirect('/dashboard')
│   ├── providers.tsx         ← QueryClientProvider wrapper
│   │
│   ├── (auth)/               ← Auth route group (no sidebar)
│   │   ├── layout.tsx        ← Centered card layout
│   │   └── login/page.tsx    ← Login page
│   │
│   └── (dashboard)/          ← Protected route group
│       ├── layout.tsx        ← Sidebar + Header + auth guard
│       ├── dashboard/        ← KPI cards + pipeline charts
│       ├── leads/            ← TanStack Table with filters/sort/pagination
│       ├── pipeline/         ← Kanban drag-and-drop board
│       ├── activities/       ← Activity log table
│       ├── analytics/        ← Extended analytics (Phase 2)
│       └── users/            ← User management (Admin only)
│
├── components/
│   ├── ui/                   ← Shadcn/UI components (auto-generated)
│   ├── auth/
│   │   └── LoginForm.tsx     ← Login form with Zod validation
│   ├── leads/
│   │   ├── columns.tsx       ← TanStack Table column definitions
│   │   └── LeadsDataTable.tsx← Full table: search, stage filter, sort, paginate
│   └── layout/
│       ├── Sidebar.tsx       ← Role-aware nav with admin section
│       └── Header.tsx        ← Page title + notifications
│
├── hooks/
│   ├── useAuth.ts            ← login(), logout(), fetchMe()
│   ├── useLeads.ts           ← React Query CRUD hooks
│   └── usePermissions.ts     ← Role-based UI guards
│
├── lib/
│   └── api.ts                ← Axios instance + JWT interceptors + auto-refresh
│
├── stores/
│   └── authStore.ts          ← Zustand: user, accessToken, refreshToken (persisted)
│
├── types/
│   ├── auth.ts               ← AuthTokens, LoginCredentials, JwtPayload
│   ├── lead.ts               ← Lead, Activity, stage/priority constants
│   └── user.ts               ← User, UserRole, ROLE_LABELS
│
├── middleware.ts              ← Next.js route guard (redirect to /login if no token)
├── .env.local                 ← (git-ignored, copied from .env.local.example)
└── .env.local.example
```

---

## 6. Database Schema

### Entity Relationship

```
users
├── id          UUID PK
├── email       VARCHAR(255) UNIQUE
├── full_name   VARCHAR(255)
├── hashed_password VARCHAR(255)
├── role        ENUM(admin, sales_manager, sales_agent, viewer)
├── is_active   BOOLEAN
├── created_at  TIMESTAMPTZ
└── updated_at  TIMESTAMPTZ
      │
      │ 1:N (created_by)
      │ 1:N (assigned_to)
      ▼
leads
├── id                  UUID PK
├── title               VARCHAR(255)
├── company_name        VARCHAR(255)
├── contact_name        VARCHAR(255)
├── email               VARCHAR(255)
├── phone               VARCHAR(50)
├── stage               ENUM(new, contacted, qualified, proposal, negotiation, won, lost)
├── priority            ENUM(low, medium, high)
├── source              ENUM(website, referral, cold_call, social_media, email_campaign, trade_show, other)
├── value               DECIMAL(15,2)
├── notes               TEXT
├── expected_close_date DATE
├── assigned_to_id      FK → users.id  (SET NULL on delete)
├── created_by_id       FK → users.id  (RESTRICT on delete)
├── created_at          TIMESTAMPTZ
└── updated_at          TIMESTAMPTZ
      │
      │ 1:N
      ▼
activities
├── id           UUID PK
├── lead_id      FK → leads.id  (CASCADE on delete)
├── user_id      FK → users.id  (CASCADE on delete)
├── type         ENUM(call, email, meeting, note, task)
├── description  TEXT
├── due_date     TIMESTAMPTZ
├── completed_at TIMESTAMPTZ
└── created_at   TIMESTAMPTZ
```

### Indexes
| Table | Index | Columns |
|-------|-------|---------|
| users | ix_users_email | email |
| leads | ix_leads_stage | stage |
| leads | ix_leads_email | email |
| leads | ix_leads_assigned_to_id | assigned_to_id |
| activities | ix_activities_lead_id | lead_id |

---

## 7. RBAC — Role-Based Access Control

### Roles

| Role | Description |
|------|-------------|
| **admin** | Full system access: manage all leads, all users, system settings |
| **sales_manager** | View/edit all leads; view all team reports; cannot manage users |
| **sales_agent** | Create and manage own leads only; add activities |
| **viewer** | Read-only access to leads and reports; cannot create or modify |

### Permission Matrix

| Action | admin | sales_manager | sales_agent | viewer |
|--------|-------|---------------|-------------|--------|
| Create lead | ✓ | ✓ | ✓ | ✗ |
| View all leads | ✓ | ✓ | own only | ✓ |
| Edit any lead | ✓ | ✓ | own only | ✗ |
| Delete lead | ✓ | ✓ | ✗ | ✗ |
| Change stage | ✓ | ✓ | own only | ✗ |
| Add activity | ✓ | ✓ | ✓ | ✗ |
| View users | ✓ | ✗ | ✗ | ✗ |
| Create user | ✓ | ✗ | ✗ | ✗ |
| Delete user | ✓ | ✗ | ✗ | ✗ |
| View analytics | ✓ | ✓ | own only | ✓ |
| Export data | ✓ | ✓ | ✗ | ✗ |

### Implementation
- **Backend**: `require_roles()` FastAPI dependency raises `HTTP 403` if role not allowed
- **Frontend**: `usePermissions()` hook hides/disables UI elements; route-level check in `layout.tsx`
- **Middleware**: `middleware.ts` redirects unauthenticated requests to `/login`

---

## 8. CRM Lead Lifecycle

### Stage Flow

```
 ┌─────┐    ┌───────────┐    ┌───────────┐    ┌──────────┐
 │ New │───▶│ Contacted │───▶│ Qualified │───▶│ Proposal │
 └─────┘    └───────────┘    └───────────┘    └──────────┘
                                                     │
                                                     ▼
                                            ┌─────────────────┐
                                            │  Negotiation    │
                                            └────────┬────────┘
                                                     │
                                          ┌──────────┴──────────┐
                                          ▼                     ▼
                                       ┌─────┐             ┌──────┐
                                       │ Won │             │ Lost │
                                       └─────┘             └──────┘
```

### Stage Definitions

| Stage | Definition | Typical Duration | Key Activity |
|-------|-----------|-----------------|--------------|
| **New** | Lead entered system (form, import, manual) | 0–1 day | Auto-assign to agent |
| **Contacted** | First outreach attempt made | 1–3 days | Phone call / email |
| **Qualified** | Meets BANT: Budget, Authority, Need, Timeline | 3–7 days | Discovery call |
| **Proposal** | Solution & pricing presented | 1–2 weeks | Proposal sent |
| **Negotiation** | Buyer reviewing terms, pricing discussion | 1–4 weeks | Multiple follow-ups |
| **Won** | Deal closed, contract signed | — | Handoff to onboarding |
| **Lost** | Deal rejected, went inactive, or to competitor | — | Log reason, nurture |

### Key Metrics per Stage
- **Conversion rate**: % of leads advancing to next stage
- **Average days in stage**: Detect bottlenecks
- **Win rate**: Won ÷ (Won + Lost) × 100
- **Pipeline value**: Sum of `value` for all non-terminal stages

---

## 9. API Reference

### Base URL
```
http://localhost:8000/api/v1
```

### Interactive Docs
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login` | Login → returns access + refresh tokens |
| POST | `/auth/refresh` | Refresh access token |
| GET | `/auth/me` | Get current user profile |

### Users (Admin only)

| Method | Endpoint | Auth |
|--------|----------|------|
| GET | `/users` | Admin |
| POST | `/users` | Admin |
| GET | `/users/{id}` | Admin or self |
| PUT | `/users/{id}` | Admin or self (no role change) |
| DELETE | `/users/{id}` | Admin |

### Leads

| Method | Endpoint | Auth | Notes |
|--------|----------|------|-------|
| GET | `/leads` | All | Role-filtered; supports `?page`, `?page_size`, `?stage`, `?search` |
| POST | `/leads` | Agent+ | Creates lead with caller as `created_by` |
| GET | `/leads/{id}` | All | Agent sees own leads only |
| PUT | `/leads/{id}` | Agent+ | Agent can only edit own |
| PATCH | `/leads/{id}/stage` | Agent+ | Stage transition |
| DELETE | `/leads/{id}` | Manager+ | |
| GET | `/leads/{id}/activities` | All | |
| POST | `/leads/{id}/activities` | Agent+ | |

### Analytics

| Method | Endpoint | Auth | Returns |
|--------|----------|------|---------|
| GET | `/analytics/dashboard` | All | KPI totals, win rate, pipeline value |
| GET | `/analytics/pipeline` | All | Count + value per stage |

---

## 10. Environment Variables

### Backend — `leadpulse-backend/.env`

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | LeadPulse CRM | Application name shown in Swagger |
| `DEBUG` | false | Enable SQLAlchemy query logging |
| `DATABASE_URL` | sqlite:///./leadpulse.db | SQLAlchemy connection string |
| `SECRET_KEY` | (change me) | JWT signing secret — **must** be changed in production |
| `ALGORITHM` | HS256 | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh token lifetime |
| `CORS_ORIGINS` | http://localhost:3000 | Comma-separated allowed origins |
| `FIRST_ADMIN_EMAIL` | admin@leadpulse.com | Seeded on first startup |
| `FIRST_ADMIN_PASSWORD` | Admin@123 | **Change before production!** |
| `FIRST_ADMIN_NAME` | System Admin | Display name of seeded admin |

### Frontend — `leadpulse-frontend/.env.local`

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | http://localhost:8000 | FastAPI backend base URL |

---

## 11. Setup & Run Instructions

### Prerequisites

| Tool | Version |
|------|---------|
| Python | 3.11+ |
| Node.js | 18+ |
| npm | 9+ |

---

### Backend Setup

```bash
# 1. Navigate to backend
cd leadpulse-backend

# 2. Create and activate virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate       # macOS / Linux
# .venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment file
cp .env.example .env
# Edit .env — change SECRET_KEY, FIRST_ADMIN_PASSWORD for production

# 5. Apply database migrations
alembic upgrade head
# This creates leadpulse.db (SQLite) and all tables

# 6. Start the development server
uvicorn app.main:app --reload --port 8000
```

**On first startup**, the admin user is auto-seeded:
- Email: `admin@leadpulse.com`
- Password: `Admin@123`

API Documentation available at: http://localhost:8000/docs

---

### Frontend Setup

```bash
# 1. Navigate to frontend
cd leadpulse-frontend

# 2. Install dependencies
npm install

# 3. Create environment file
cp .env.local.example .env.local
# Edit NEXT_PUBLIC_API_URL if backend runs on a different port/host

# 4. Start the development server
npm run dev
```

Application available at: http://localhost:3000

---

### Full Stack (both services)

```bash
# Terminal 1 — Backend
cd leadpulse-backend && uvicorn app.main:app --reload --port 8000

# Terminal 2 — Frontend
cd leadpulse-frontend && npm run dev
```

**Login at** http://localhost:3000/login with `admin@leadpulse.com` / `Admin@123`

---

### Production Build

```bash
# Frontend
cd leadpulse-frontend && npm run build && npm start

# Backend (with production ASGI settings)
cd leadpulse-backend
# Change DATABASE_URL to PostgreSQL in .env
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## 12. Development Roadmap

### Phase 1 — Foundation (Current) ✅
- [x] FastAPI backend scaffold (models, schemas, CRUD, JWT auth, RBAC)
- [x] Next.js 14 frontend scaffold (App Router, Shadcn/UI, TailwindCSS)
- [x] Lead CRUD with role-based filtering
- [x] TanStack Table data grid (sort, filter, pagination, row actions)
- [x] Kanban pipeline board (drag-and-drop stage updates)
- [x] Dashboard KPI cards and charts (Recharts)
- [x] Activity log (calls, emails, meetings, notes, tasks)
- [x] User management panel (Admin only)
- [x] JWT access + refresh token auth with auto-refresh
- [x] Zustand auth state with localStorage persistence
- [x] SQLite → PostgreSQL migration-ready schema (Alembic)

### Phase 2 — Enhancement
- [ ] Lead detail page with full activity timeline
- [ ] Create/Edit lead dialog (React Hook Form + Zod)
- [ ] Bulk lead import (CSV upload)
- [ ] Lead assignment workflow (auto-assign by round-robin)
- [ ] Email notifications (FastAPI-Mail)
- [ ] Real-time lead update notifications (WebSocket / SSE)
- [ ] Activity reminders and due date alerts
- [ ] User invite flow (email-based)

### Phase 3 — Advanced CRM
- [ ] Lead scoring model (rule-based or ML)
- [ ] Custom pipeline stages (admin-configurable)
- [ ] Email integration (Gmail/Outlook OAuth, sync emails to activities)
- [ ] Calendar integration (Google Calendar)
- [ ] Reporting exports (CSV, PDF)
- [ ] Mobile-responsive optimizations
- [ ] Multi-tenancy support (workspace isolation)

### Phase 4 — Operations
- [ ] Docker + Docker Compose setup
- [ ] CI/CD pipeline (GitHub Actions)
- [ ] Production PostgreSQL configuration
- [ ] Redis caching layer
- [ ] Rate limiting (slowapi)
- [ ] Audit log (all state changes tracked)
- [ ] GDPR compliance (data export, deletion)

---

## Appendix — Technology Links

| Technology | Documentation |
|------------|--------------|
| FastAPI | https://fastapi.tiangolo.com |
| SQLAlchemy 2.0 | https://docs.sqlalchemy.org/en/20/ |
| Alembic | https://alembic.sqlalchemy.org |
| Pydantic v2 | https://docs.pydantic.dev/latest/ |
| python-jose | https://python-jose.readthedocs.io |
| Next.js 14 | https://nextjs.org/docs |
| Shadcn/UI | https://ui.shadcn.com |
| TailwindCSS | https://tailwindcss.com/docs |
| TanStack Table | https://tanstack.com/table |
| TanStack Query | https://tanstack.com/query |
| Zustand | https://zustand-demo.pmnd.rs |
| Recharts | https://recharts.org |
| Zod | https://zod.dev |
| Sonner | https://sonner.emilkowal.ski |

---

*Generated: June 2026 | LeadPulse CRM v1.0.0*
