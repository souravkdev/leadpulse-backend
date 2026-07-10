from calendar import monthrange
from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.core.rbac import can_use_attendance
from app.core.timezone import now_in_tz, work_date_for_user
from app.models.attendance import (
    AttendanceCorrection,
    AttendanceSession,
    AttendanceSessionStatus,
    AttendanceSettings,
    BreakRecord,
    BreakType,
    CorrectionStatus,
    LeaveApplication,
    LeaveBalance,
    LeavePolicy,
    LeaveStatus,
    LeaveType,
    ShiftAssignment,
    ShiftTemplate,
    UserAttendanceProfile,
)
from app.models.user import User, UserRole


def ensure_attendance_access(user: User) -> None:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is inactive.")
    if not can_use_attendance(user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Attendance not available for viewers.")


def get_or_create_profile(db: Session, user: User) -> UserAttendanceProfile:
    profile = (
        db.query(UserAttendanceProfile)
        .filter(UserAttendanceProfile.user_id == user.id)
        .first()
    )
    if not profile:
        profile = UserAttendanceProfile(
            user_id=user.id,
            attendance_enabled=user.role != UserRole.viewer,
        )
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def ensure_attendance_settings(db: Session) -> AttendanceSettings:
    row = db.query(AttendanceSettings).first()
    if not row:
        from app.config import get_settings

        row = AttendanceSettings(company_timezone=get_settings().COMPANY_TIMEZONE)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def get_shift_for_date(db: Session, user_id: str, work_date) -> ShiftAssignment | None:
    return (
        db.query(ShiftAssignment)
        .options(joinedload(ShiftAssignment.shift_template))
        .filter(
            ShiftAssignment.user_id == user_id,
            ShiftAssignment.assignment_date == work_date,
        )
        .first()
    )


def resolve_shift_assignment_range(
    start_date: date | None, end_date: date | None
) -> tuple[date, date]:
    today = date.today()
    if start_date is None and end_date is None:
        first = today.replace(day=1)
        _, last_day = monthrange(today.year, today.month)
        return first, date(today.year, today.month, last_day)
    if start_date is not None and end_date is None:
        _, last_day = monthrange(start_date.year, start_date.month)
        return start_date, date(start_date.year, start_date.month, last_day)
    if start_date is None and end_date is not None:
        first = end_date.replace(day=1)
        return first, end_date
    assert start_date is not None and end_date is not None
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be on or after start date.",
        )
    return start_date, end_date


def assign_shift_range(
    db: Session,
    user_id: str,
    shift_template_id: str,
    start_date: date | None,
    end_date: date | None,
) -> tuple[date, date, int]:
    start, end = resolve_shift_assignment_range(start_date, end_date)
    count = 0
    current = start
    while current <= end:
        existing = (
            db.query(ShiftAssignment)
            .filter(
                ShiftAssignment.user_id == user_id,
                ShiftAssignment.assignment_date == current,
            )
            .first()
        )
        if existing:
            existing.shift_template_id = shift_template_id
        else:
            db.add(
                ShiftAssignment(
                    user_id=user_id,
                    shift_template_id=shift_template_id,
                    assignment_date=current,
                )
            )
        count += 1
        current += timedelta(days=1)
    db.commit()
    return start, end, count


def summarize_shift_assignments(db: Session) -> list[dict]:
    assignments = (
        db.query(ShiftAssignment)
        .options(joinedload(ShiftAssignment.shift_template), joinedload(ShiftAssignment.user))
        .order_by(
            ShiftAssignment.user_id,
            ShiftAssignment.shift_template_id,
            ShiftAssignment.assignment_date,
        )
        .all()
    )

    summaries: list[dict] = []
    current: dict | None = None

    for assignment in assignments:
        user_name = assignment.user.full_name if assignment.user else None
        shift_name = assignment.shift_template.name if assignment.shift_template else None

        if (
            current
            and current["user_id"] == assignment.user_id
            and current["shift_template_id"] == assignment.shift_template_id
            and assignment.assignment_date == current["end_date"] + timedelta(days=1)
        ):
            current["end_date"] = assignment.assignment_date
            current["days_count"] += 1
        else:
            if current:
                summaries.append(current)
            current = {
                "user_id": assignment.user_id,
                "user_name": user_name,
                "shift_template_id": assignment.shift_template_id,
                "shift_name": shift_name,
                "start_date": assignment.assignment_date,
                "end_date": assignment.assignment_date,
                "days_count": 1,
            }

    if current:
        summaries.append(current)

    summaries.sort(key=lambda row: row["start_date"], reverse=True)
    return summaries


def delete_shift_assignment_range(
    db: Session,
    user_id: str,
    shift_template_id: str,
    start_date: date,
    end_date: date,
) -> int:
    deleted = (
        db.query(ShiftAssignment)
        .filter(
            ShiftAssignment.user_id == user_id,
            ShiftAssignment.shift_template_id == shift_template_id,
            ShiftAssignment.assignment_date >= start_date,
            ShiftAssignment.assignment_date <= end_date,
        )
        .delete()
    )
    db.commit()
    return deleted


def get_today_session(db: Session, user: User) -> AttendanceSession | None:
    work_date = work_date_for_user(db, user.id)
    # Prioritize active sessions (clocked_in or on_break)
    active = (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(
            AttendanceSession.user_id == user.id,
            AttendanceSession.work_date == work_date,
            AttendanceSession.status.in_([AttendanceSessionStatus.clocked_in, AttendanceSessionStatus.on_break])
        )
        .first()
    )
    if active:
        return active
    
    # Return latest clocked out session for today
    return (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(
            AttendanceSession.user_id == user.id,
            AttendanceSession.work_date == work_date,
        )
        .order_by(AttendanceSession.clock_in_at.desc())
        .first()
    )


def compute_elapsed_minutes(session: AttendanceSession) -> tuple[int, int]:
    now = datetime.now(session.clock_in_at.tzinfo)
    end = session.clock_out_at or now
    total_elapsed = int((end - session.clock_in_at).total_seconds() // 60)
    break_mins = session.total_break_minutes
    active_break = next((b for b in session.breaks if b.end_at is None), None)
    if active_break:
        active_mins = int((now - active_break.start_at).total_seconds() // 60)
        break_mins += active_mins
    work_mins = max(0, total_elapsed - break_mins)
    return work_mins, break_mins


def session_missing_clock_out(session: AttendanceSession, today: date) -> bool:
    if session.work_date >= today:
        return False
    if session.clock_out_at is None:
        return True
    return session.status in (
        AttendanceSessionStatus.clocked_in,
        AttendanceSessionStatus.on_break,
    )


def clock_in(db: Session, user: User) -> AttendanceSession:
    ensure_attendance_access(user)
    get_or_create_profile(db, user)
    work_date = work_date_for_user(db, user.id)
    
    # Check if there is an active session
    active = (
        db.query(AttendanceSession)
        .filter(
            AttendanceSession.user_id == user.id,
            AttendanceSession.work_date == work_date,
            AttendanceSession.status.in_([AttendanceSessionStatus.clocked_in, AttendanceSessionStatus.on_break])
        )
        .first()
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already clocked in.",
        )

    shift = get_shift_for_date(db, user.id, work_date)
    now = now_in_tz(db, user.id)

    session = AttendanceSession(
        user_id=user.id,
        work_date=work_date,
        status=AttendanceSessionStatus.clocked_in,
        clock_in_at=now,
        shift_assignment_id=shift.id if shift else None,
        shift_warning=shift is None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(AttendanceSession.id == session.id)
        .first()
    )


def clock_out(db: Session, user: User) -> AttendanceSession:
    ensure_attendance_access(user)
    session = get_today_session(db, user)
    if not session:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not clocked in today.")
    if session.status == AttendanceSessionStatus.on_break:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End your break before clocking out.")
    if session.status == AttendanceSessionStatus.clocked_out:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Already clocked out.")

    session.clock_out_at = now_in_tz(db, user.id)
    session.status = AttendanceSessionStatus.clocked_out
    db.commit()
    db.refresh(session)
    return (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(AttendanceSession.id == session.id)
        .first()
    )


def start_break(db: Session, user: User, break_type: BreakType) -> AttendanceSession:
    ensure_attendance_access(user)
    session = get_today_session(db, user)
    if not session or session.status != AttendanceSessionStatus.clocked_in:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Must be clocked in to start a break.")

    if break_type == BreakType.lunch:
        work_date = work_date_for_user(db, user.id)
        all_sessions = (
            db.query(AttendanceSession)
            .options(joinedload(AttendanceSession.breaks))
            .filter(
                AttendanceSession.user_id == user.id,
                AttendanceSession.work_date == work_date,
            )
            .all()
        )
        lunch_count = sum(
            1 for s in all_sessions for b in s.breaks if b.break_type == BreakType.lunch
        )
        if lunch_count >= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Lunch break already taken today.",
            )

    now = now_in_tz(db, user.id)
    db.add(BreakRecord(session_id=session.id, break_type=break_type, start_at=now))
    session.status = AttendanceSessionStatus.on_break
    db.commit()
    return (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(AttendanceSession.id == session.id)
        .first()
    )


def end_break(db: Session, user: User) -> AttendanceSession:
    ensure_attendance_access(user)
    session = get_today_session(db, user)
    if not session or session.status != AttendanceSessionStatus.on_break:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active break.")

    active = (
        db.query(BreakRecord)
        .filter(BreakRecord.session_id == session.id, BreakRecord.end_at.is_(None))
        .first()
    )
    if not active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active break found.")

    now = now_in_tz(db, user.id)
    active.end_at = now
    active.duration_minutes = int((now - active.start_at).total_seconds() // 60)
    session.total_break_minutes += active.duration_minutes
    session.status = AttendanceSessionStatus.clocked_in
    db.commit()
    return (
        db.query(AttendanceSession)
        .options(joinedload(AttendanceSession.breaks))
        .filter(AttendanceSession.id == session.id)
        .first()
    )


def create_correction(db: Session, user: User, data) -> AttendanceCorrection:
    ensure_attendance_access(user)
    session = None
    if data.session_id:
        session = db.get(AttendanceSession, data.session_id)
        if not session or session.user_id != user.id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")

    correction = AttendanceCorrection(
        user_id=user.id,
        session_id=data.session_id,
        work_date=data.work_date,
        original_clock_in_at=session.clock_in_at if session else None,
        original_clock_out_at=session.clock_out_at if session else None,
        requested_clock_in_at=data.requested_clock_in_at,
        requested_clock_out_at=data.requested_clock_out_at,
        reason=data.reason,
    )
    db.add(correction)
    db.commit()
    db.refresh(correction)
    return correction


def approve_correction(db: Session, correction: AttendanceCorrection, reviewer: User, notes: str | None) -> AttendanceCorrection:
    if correction.status != CorrectionStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Correction already reviewed.")

    session = None
    if correction.session_id:
        session = db.get(AttendanceSession, correction.session_id)
    else:
        session = (
            db.query(AttendanceSession)
            .filter(
                AttendanceSession.user_id == correction.user_id,
                AttendanceSession.work_date == correction.work_date,
            )
            .first()
        )

    if not session and (correction.requested_clock_in_at or correction.requested_clock_out_at):
        session = AttendanceSession(
            user_id=correction.user_id,
            work_date=correction.work_date,
            status=AttendanceSessionStatus.clocked_out,
            clock_in_at=correction.requested_clock_in_at or correction.requested_clock_out_at,
            clock_out_at=correction.requested_clock_out_at,
            shift_warning=True,
        )
        db.add(session)
        db.flush()
        correction.session_id = session.id

    if session:
        if correction.requested_clock_in_at:
            session.clock_in_at = correction.requested_clock_in_at
        if correction.requested_clock_out_at:
            session.clock_out_at = correction.requested_clock_out_at
            session.status = AttendanceSessionStatus.clocked_out

    correction.status = CorrectionStatus.approved
    correction.reviewer_id = reviewer.id
    correction.reviewer_notes = notes
    from datetime import timezone
    correction.reviewed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(correction)
    return correction


# ── Leave helpers ─────────────────────────────────────────────────────────────

def count_leave_days(start_date, end_date, is_half_day: bool) -> Decimal:
    if is_half_day:
        return Decimal("0.5")
    days = (end_date - start_date).days + 1
    return Decimal(str(max(days, 1)))


def get_leave_balance(db: Session, user_id: str, leave_type: LeaveType) -> LeaveBalance:
    balance = (
        db.query(LeaveBalance)
        .filter(LeaveBalance.user_id == user_id, LeaveBalance.leave_type == leave_type)
        .first()
    )
    if not balance:
        balance = LeaveBalance(user_id=user_id, leave_type=leave_type)
        db.add(balance)
        db.commit()
        db.refresh(balance)
    return balance


def has_overlapping_leave(db: Session, user_id: str, start_date, end_date, exclude_id: str | None = None) -> bool:
    q = db.query(LeaveApplication).filter(
        LeaveApplication.user_id == user_id,
        LeaveApplication.status.in_([LeaveStatus.pending, LeaveStatus.approved]),
        LeaveApplication.start_date <= end_date,
        LeaveApplication.end_date >= start_date,
    )
    if exclude_id:
        q = q.filter(LeaveApplication.id != exclude_id)
    return q.first() is not None


def run_monthly_accrual(db: Session) -> dict:
    policies = db.query(LeavePolicy).filter(LeavePolicy.is_active.is_(True)).all()
    users = db.query(User).filter(User.is_active.is_(True), User.role != UserRole.viewer).all()
    count = 0
    for user in users:
        for policy in policies:
            balance = get_leave_balance(db, user.id, policy.leave_type)
            balance.accrued += policy.accrual_per_month
            count += 1
    db.commit()
    return {"users_processed": len(users), "balances_updated": count}
