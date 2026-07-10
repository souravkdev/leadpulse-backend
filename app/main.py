from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import router as api_router
from app.config import get_settings
from app.database import engine, Base
from app.core.security import hash_password
from sqlalchemy.orm import Session
from app.models.user import User, UserRole

settings = get_settings()


def _seed_admin() -> None:
    """Create the first admin user if no users exist."""

    with Session(engine) as db:
        if db.query(User).count() == 0:
            admin = User(
                email=settings.FIRST_ADMIN_EMAIL,
                full_name=settings.FIRST_ADMIN_NAME,
                hashed_password=hash_password(settings.FIRST_ADMIN_PASSWORD),
                role=UserRole.admin,
            )
            db.add(admin)
            db.commit()
            print(f"[seed] Admin user created → {settings.FIRST_ADMIN_EMAIL}")


def _seed_attendance_defaults() -> None:
    from decimal import Decimal
    from app.models.attendance import AttendanceSettings, LeavePolicy, LeaveType
    from app.services.attendance_service import ensure_attendance_settings

    with Session(engine) as db:
        ensure_attendance_settings(db)
        defaults = [
            (LeaveType.paid, Decimal("1.0")),
            (LeaveType.sick, Decimal("1.0")),
        ]
        for leave_type, accrual in defaults:
            if not db.query(LeavePolicy).filter(LeavePolicy.leave_type == leave_type).first():
                db.add(LeavePolicy(leave_type=leave_type, accrual_per_month=accrual))
        db.commit()
        print("[seed] Attendance defaults ensured")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    import app.models  # noqa: F401

    # SQLite local dev only — PostgreSQL schema is managed by Alembic migrations.
    if settings.DATABASE_URL.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)

    try:
        _seed_admin()
        _seed_attendance_defaults()
    except Exception as exc:
        print(f"[seed] Skipped startup seed: {exc}")

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.APP_VERSION}
