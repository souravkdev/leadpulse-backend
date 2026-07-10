from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user, get_db
from app.core.rbac import can_use_attendance
from app.core.timezone import work_date_for_user
from app.models.attendance import (
    AttendanceCorrection,
    AttendanceSession,
    AttendanceSessionStatus,
    BreakType,
    CorrectionStatus,
    LeaveApplication,
    LeaveStatus,
)
from app.models.user import User
from app.schemas.attendance import (
    AttendanceSessionListResponse,
    AttendanceSessionRead,
    BreakRecordRead,
    BreakStartRequest,
    CalendarDayEntry,
    CalendarResponse,
    CorrectionCreate,
    CorrectionRead,
    DayAttendanceDetail,
    DaySessionDetail,
    TodayAttendanceResponse,
)
from app.services import attendance_service as svc

router = APIRouter(prefix="/attendance", tags=["Attendance"])


def _require_attendance(user: User) -> None:
    if not can_use_attendance(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance not available.")


def _shift_info(shift):
    if shift and shift.shift_template:
        tmpl = shift.shift_template
        return tmpl.name, tmpl.start_time, tmpl.end_time
    return None, None, None


@router.get("/today", response_model=TodayAttendanceResponse)
def get_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_attendance(current_user)
    session = svc.get_today_session(db, current_user)
    work_date = work_date_for_user(db, current_user.id)
    shift = svc.get_shift_for_date(db, current_user.id, work_date)
    shift_name, shift_start, shift_end = _shift_info(shift)

    # Resolve break settings
    lunch_mins = 30
    short_mins = 15
    if shift and shift.shift_template:
        lunch_mins = shift.shift_template.lunch_break_minutes
        short_mins = shift.shift_template.short_break_minutes

    if not session:
        return TodayAttendanceResponse(
            session=None,
            shift_warning=shift is None,
            shift_name=shift_name,
            shift_start_time=shift_start,
            shift_end_time=shift_end,
            lunch_break_minutes=lunch_mins,
            short_break_minutes=short_mins,
        )

    # Retroactively update session shift assignment if one was created later
    if not session.shift_assignment_id and shift:
        session.shift_assignment_id = shift.id
        session.shift_warning = False
        db.commit()

    # Aggregate elapsed minutes across all sessions for today
    all_sessions = (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(
            AttendanceSession.user_id == current_user.id,
            AttendanceSession.work_date == session.work_date,
        )
        .all()
    )

    total_work_mins = 0
    total_break_mins = 0
    lunch_breaks_taken = 0

    for s in all_sessions:
        work_mins, break_mins = svc.compute_elapsed_minutes(s)
        total_work_mins += work_mins
        total_break_mins += break_mins
        for b in s.breaks:
            if b.break_type == BreakType.lunch:
                lunch_breaks_taken += 1

    active_break = next((b for b in session.breaks if b.end_at is None), None)

    return TodayAttendanceResponse(
        session=AttendanceSessionRead.model_validate(session),
        shift_warning=shift is None,
        shift_name=shift_name,
        shift_start_time=shift_start,
        shift_end_time=shift_end,
        elapsed_work_minutes=total_work_mins,
        elapsed_break_minutes=total_break_mins,
        active_break=BreakRecordRead.model_validate(active_break) if active_break else None,
        lunch_breaks_taken=lunch_breaks_taken,
        lunch_break_minutes=lunch_mins,
        short_break_minutes=short_mins,
    )


@router.post("/clock-in", response_model=AttendanceSessionRead)
def clock_in(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = svc.clock_in(db, current_user)
    return AttendanceSessionRead.model_validate(session)


@router.post("/clock-out", response_model=AttendanceSessionRead)
def clock_out(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = svc.clock_out(db, current_user)
    return AttendanceSessionRead.model_validate(session)


@router.post("/break/start", response_model=AttendanceSessionRead)
def break_start(
    payload: BreakStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = svc.start_break(db, current_user, payload.break_type)
    return AttendanceSessionRead.model_validate(session)


@router.post("/break/end", response_model=AttendanceSessionRead)
def break_end(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    session = svc.end_break(db, current_user)
    return AttendanceSessionRead.model_validate(session)


@router.get("/calendar", response_model=CalendarResponse)
def get_calendar(
    month: str = Query(..., pattern=r"^\d{4}-\d{2}$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_attendance(current_user)
    year, mon = map(int, month.split("-"))
    from calendar import monthrange

    _, last_day = monthrange(year, mon)
    start = date(year, mon, 1)
    end = date(year, mon, last_day)

    sessions = (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(
            AttendanceSession.user_id == current_user.id,
            AttendanceSession.work_date >= start,
            AttendanceSession.work_date <= end,
        )
        .order_by(AttendanceSession.clock_in_at.asc())
        .all()
    )
    sessions_by_date: dict[date, list[AttendanceSession]] = {}
    for s in sessions:
        sessions_by_date.setdefault(s.work_date, []).append(s)

    user_today = work_date_for_user(db, current_user.id)

    leaves = (
        db.query(LeaveApplication)
        .filter(
            LeaveApplication.user_id == current_user.id,
            LeaveApplication.status == LeaveStatus.approved,
            LeaveApplication.start_date <= end,
            LeaveApplication.end_date >= start,
        )
        .all()
    )

    days: list[CalendarDayEntry] = []
    from datetime import timedelta

    current = start
    while current <= end:
        leave_for_day = next(
            (l for l in leaves if l.start_date <= current <= l.end_date),
            None,
        )
        day_sessions = sessions_by_date.get(current, [])
        sess = day_sessions[-1] if day_sessions else None
        has_missing = any(
            svc.session_missing_clock_out(s, user_today) for s in day_sessions
        )
        days.append(
            CalendarDayEntry(
                date=current,
                session=AttendanceSessionRead.model_validate(sess) if sess else None,
                on_leave=leave_for_day is not None,
                leave_type=leave_for_day.leave_type if leave_for_day else None,
                is_half_day=leave_for_day.is_half_day if leave_for_day else False,
                has_missing_clock_out=has_missing,
            )
        )
        current += timedelta(days=1)

    return CalendarResponse(month=month, days=days)


@router.get("/day", response_model=DayAttendanceDetail)
def get_day_detail(
    day: date = Query(..., alias="date"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_attendance(current_user)
    user_today = work_date_for_user(db, current_user.id)

    sessions = (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(
            AttendanceSession.user_id == current_user.id,
            AttendanceSession.work_date == day,
        )
        .order_by(AttendanceSession.clock_in_at.asc())
        .all()
    )

    pending_corrections = (
        db.query(AttendanceCorrection)
        .filter(
            AttendanceCorrection.user_id == current_user.id,
            AttendanceCorrection.work_date == day,
            AttendanceCorrection.status == CorrectionStatus.pending,
        )
        .all()
    )
    correction_by_session = {
        c.session_id: c.id for c in pending_corrections if c.session_id
    }

    leave_for_day = (
        db.query(LeaveApplication)
        .filter(
            LeaveApplication.user_id == current_user.id,
            LeaveApplication.status == LeaveStatus.approved,
            LeaveApplication.start_date <= day,
            LeaveApplication.end_date >= day,
        )
        .first()
    )

    session_details: list[DaySessionDetail] = []
    total_work = 0
    total_break = 0
    has_missing = False

    for s in sessions:
        work_mins, break_mins = svc.compute_elapsed_minutes(s)
        missing = svc.session_missing_clock_out(s, user_today)
        has_missing = has_missing or missing
        total_work += work_mins
        total_break += break_mins
        session_details.append(
            DaySessionDetail(
                id=s.id,
                clock_in_at=s.clock_in_at,
                clock_out_at=s.clock_out_at,
                status=s.status,
                breaks=[BreakRecordRead.model_validate(b) for b in s.breaks],
                work_minutes=work_mins,
                break_minutes=break_mins,
                missing_clock_out=missing,
                pending_correction_id=correction_by_session.get(s.id),
            )
        )

    return DayAttendanceDetail(
        date=day,
        on_leave=leave_for_day is not None,
        leave_type=leave_for_day.leave_type if leave_for_day else None,
        is_half_day=leave_for_day.is_half_day if leave_for_day else False,
        half_day_period=leave_for_day.half_day_period if leave_for_day else None,
        sessions=session_details,
        total_work_minutes=total_work,
        total_break_minutes=total_break,
        has_missing_clock_out=has_missing,
    )


@router.get("/sessions", response_model=AttendanceSessionListResponse)
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_attendance(current_user)
    q = (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(AttendanceSession.user_id == current_user.id)
        .order_by(AttendanceSession.work_date.desc())
    )
    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()
    return AttendanceSessionListResponse(
        items=[AttendanceSessionRead.model_validate(s) for s in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/corrections", response_model=CorrectionRead, status_code=status.HTTP_201_CREATED)
def submit_correction(
    payload: CorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    correction = svc.create_correction(db, current_user, payload)
    return CorrectionRead.model_validate(correction)


@router.get("/corrections", response_model=list[CorrectionRead])
def list_corrections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    _require_attendance(current_user)
    items = (
        db.query(AttendanceCorrection)
        .filter(AttendanceCorrection.user_id == current_user.id)
        .order_by(AttendanceCorrection.created_at.desc())
        .all()
    )
    return [CorrectionRead.model_validate(c) for c in items]
