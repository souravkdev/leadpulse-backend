from datetime import date, datetime
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.config import get_settings
from app.models.attendance import AttendanceSettings, UserAttendanceProfile


def get_company_timezone(db: Session) -> str:
    settings_row = db.query(AttendanceSettings).first()
    if settings_row:
        return settings_row.company_timezone
    return get_settings().COMPANY_TIMEZONE


def get_effective_timezone(db: Session, user_id: str) -> ZoneInfo:
    company_tz = get_company_timezone(db)
    profile = (
        db.query(UserAttendanceProfile)
        .filter(UserAttendanceProfile.user_id == user_id)
        .first()
    )
    tz_name = profile.timezone_override if profile and profile.timezone_override else company_tz
    return ZoneInfo(tz_name)


def now_in_tz(db: Session, user_id: str) -> datetime:
    return datetime.now(get_effective_timezone(db, user_id))


def work_date_for_user(db: Session, user_id: str, at: datetime | None = None) -> date:
    tz = get_effective_timezone(db, user_id)
    dt = at.astimezone(tz) if at else datetime.now(tz)
    return dt.date()
