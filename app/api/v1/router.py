from fastapi import APIRouter

from app.api.v1 import auth, users, leads, analytics, attendance, leave, attendance_admin

router = APIRouter(prefix="/api/v1")

router.include_router(auth.router)
router.include_router(users.router)
router.include_router(leads.router)
router.include_router(analytics.router)
router.include_router(attendance.router)
router.include_router(leave.router)
router.include_router(attendance_admin.router)
