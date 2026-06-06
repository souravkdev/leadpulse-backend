# LeadPulse Backend

Backend API service for LeadPulse CRM, built with FastAPI, SQLAlchemy, and JWT authentication.

## Stack

- FastAPI 0.115.5
- SQLAlchemy 2.0
- Alembic (migrations)
- SQLite (default dev database)
- JWT auth with python-jose
- Password hashing with bcrypt

## Features

- JWT login and refresh tokens
- Role-based access control (admin, sales_manager, sales_agent, viewer)
- Lead CRUD with pipeline stages
- Lead activity logging
- Dashboard and pipeline analytics endpoints
- Auto-seeded first admin on startup

## Project Structure

- app/main.py: app bootstrap, CORS, lifespan, health endpoint
- app/api/v1/: versioned API routers
- app/models/: SQLAlchemy models
- app/schemas/: Pydantic request/response schemas
- app/core/: security and RBAC helpers
- app/config.py: environment settings
- app/database.py: engine and session setup

## Prerequisites

- Python 3.11+
- pip

## Quick Start

1) Go to backend directory
- cd /Users/apple/Projects/lead-management-system/leadpulse-backend

2) Create virtual environment
- python3 -m venv .venv
- source .venv/bin/activate

3) Install dependencies
- pip install -r requirements.txt

4) Configure environment
- cp .env.example .env

5) Run server
- uvicorn app.main:app --reload --port 8000

API will run at:
- http://localhost:8000

Swagger docs:
- http://localhost:8000/docs

ReDoc:
- http://localhost:8000/redoc

Health check:
- http://localhost:8000/health

## Default Admin Account

If no users exist, backend seeds an admin user on first startup from env values:

- FIRST_ADMIN_EMAIL (default: admin@leadpulse.com)
- FIRST_ADMIN_PASSWORD (default: Admin@123)
- FIRST_ADMIN_NAME (default: System Admin)

## Environment Variables

Configured in .env (see .env.example):

- APP_NAME: application name
- DEBUG: debug mode true/false
- DATABASE_URL: database DSN
- SECRET_KEY: JWT signing secret
- ALGORITHM: JWT algorithm, default HS256
- ACCESS_TOKEN_EXPIRE_MINUTES: access token lifetime
- REFRESH_TOKEN_EXPIRE_DAYS: refresh token lifetime
- CORS_ORIGINS: comma-separated allowed origins
- FIRST_ADMIN_EMAIL: seeded admin email
- FIRST_ADMIN_PASSWORD: seeded admin password
- FIRST_ADMIN_NAME: seeded admin full name

## Database Notes

Default dev database is SQLite:
- DATABASE_URL=sqlite:///./leadpulse.db

The app creates tables at startup and seeds the first admin if users table is empty.

For production, use PostgreSQL and run migrations via Alembic.

## API Base Path

All primary endpoints are under:
- /api/v1

Main route groups:
- /api/v1/auth
- /api/v1/users
- /api/v1/leads
- /api/v1/analytics

## Common Commands

Run tests:
- pytest

Stop auto-reload server:
- Ctrl + C

## Troubleshooting

Backend does not start:
- Ensure virtual environment is active
- Ensure requirements are installed
- Ensure .env exists and SECRET_KEY is set

Login fails:
- Verify seeded admin credentials in .env
- Delete leadpulse.db only in local dev if you need to re-seed fresh data

CORS errors:
- Add frontend origin to CORS_ORIGINS in .env
