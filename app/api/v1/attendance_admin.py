from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user, get_db
from app.core.rbac import can_manage_attendance_admin, require_roles
from app.core.timezone import work_date_for_user
from app.models.attendance import (
    AttendanceCorrection,
    AttendanceSession,
    CorrectionStatus,
    LeaveApplication,
    LeavePolicy,
    LeaveStatus,
    ShiftAssignment,
    ShiftTemplate,
    UserAttendanceProfile,
)
from app.models.user import User, UserRole
from app.schemas.attendance import (
    CorrectionRead,
    CorrectionReview,
    LeavePolicyCreate,
    LeavePolicyRead,
    LeavePolicyUpdate,
    ShiftAssignmentBulkResponse,
    ShiftAssignmentCreate,
    ShiftAssignmentDeleteResponse,
    ShiftAssignmentRead,
    ShiftAssignmentSummary,
    ShiftTemplateCreate,
    ShiftTemplateRead,
    TeamAttendanceSummary,
    UserAttendanceProfileRead,
    UserAttendanceProfileUpdate,
)
from app.services import attendance_service as svc

router = APIRouter(prefix="/attendance/admin", tags=["Attendance Admin"])

_admin_only = require_roles(UserRole.admin)


def _shift_read(a: ShiftAssignment) -> ShiftAssignmentRead:
    data = ShiftAssignmentRead.model_validate(a)
    if a.shift_template:
        data.shift_template = ShiftTemplateRead.model_validate(a.shift_template)
    if a.user:
        data.user_name = a.user.full_name
    return data


# ── Shift templates ───────────────────────────────────────────────────────────

@router.get("/shifts/templates", response_model=list[ShiftTemplateRead])
def list_shift_templates(
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    return db.query(ShiftTemplate).order_by(ShiftTemplate.name).all()


@router.post("/shifts/templates", response_model=ShiftTemplateRead, status_code=status.HTTP_201_CREATED)
def create_shift_template(
    payload: ShiftTemplateCreate,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    by_name = (
        db.query(ShiftTemplate)
        .filter(func.lower(ShiftTemplate.name) == payload.name.lower())
        .first()
    )
    if by_name:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shift template with this name already exists.",
        )
    by_timing = (
        db.query(ShiftTemplate)
        .filter(
            ShiftTemplate.start_time == payload.start_time,
            ShiftTemplate.end_time == payload.end_time,
            ShiftTemplate.days_of_week == payload.days_of_week,
        )
        .first()
    )
    if by_timing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A shift template with the same timing already exists.",
        )
    template = ShiftTemplate(**payload.model_dump())
    db.add(template)
    db.commit()
    db.refresh(template)
    return template


@router.delete("/shifts/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift_template(
    template_id: str,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    template = db.get(ShiftTemplate, template_id)
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift template not found.")
    db.delete(template)
    db.commit()


@router.get("/shifts/assignments", response_model=list[ShiftAssignmentRead])
def list_shift_assignments(
    user_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    q = (
        db.query(ShiftAssignment)
        .options(joinedload(ShiftAssignment.shift_template), joinedload(ShiftAssignment.user))
        .order_by(ShiftAssignment.assignment_date.desc())
    )
    if user_id:
        q = q.filter(ShiftAssignment.user_id == user_id)
    return [_shift_read(a) for a in q.limit(200).all()]


@router.get("/shifts/assignments/summary", response_model=list[ShiftAssignmentSummary])
def list_shift_assignment_summary(
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    return svc.summarize_shift_assignments(db)


@router.post(
    "/shifts/assignments",
    response_model=ShiftAssignmentBulkResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_shift_assignment(
    payload: ShiftAssignmentCreate,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    if not db.get(ShiftTemplate, payload.shift_template_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shift template not found.")
    if not db.get(User, payload.user_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    start, end, count = svc.assign_shift_range(
        db,
        payload.user_id,
        payload.shift_template_id,
        payload.start_date,
        payload.end_date,
    )
    return ShiftAssignmentBulkResponse(
        user_id=payload.user_id,
        shift_template_id=payload.shift_template_id,
        start_date=start,
        end_date=end,
        days_assigned=count,
    )


@router.delete("/shifts/assignments/bulk", response_model=ShiftAssignmentDeleteResponse)
def delete_shift_assignments_bulk(
    user_id: str = Query(...),
    shift_template_id: str = Query(...),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    if end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="End date must be on or after start date.",
        )
    deleted = svc.delete_shift_assignment_range(
        db, user_id, shift_template_id, start_date, end_date
    )
    return ShiftAssignmentDeleteResponse(deleted=deleted)


@router.delete("/shifts/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_shift_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    assignment = db.get(ShiftAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found.")
    db.delete(assignment)
    db.commit()


# ── Leave policies ────────────────────────────────────────────────────────────

@router.get("/policies", response_model=list[LeavePolicyRead])
def list_policies(
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    return db.query(LeavePolicy).order_by(LeavePolicy.leave_type).all()


@router.post("/policies", response_model=LeavePolicyRead, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: LeavePolicyCreate,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    existing = db.query(LeavePolicy).filter(LeavePolicy.leave_type == payload.leave_type).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Policy for this leave type already exists.")
    policy = LeavePolicy(**payload.model_dump())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.patch("/policies/{policy_id}", response_model=LeavePolicyRead)
def update_policy(
    policy_id: str,
    payload: LeavePolicyUpdate,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    policy = db.get(LeavePolicy, policy_id)
    if not policy:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(policy, field, value)
    db.commit()
    db.refresh(policy)
    return policy


@router.post("/accrue")
def run_accrual(
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    return svc.run_monthly_accrual(db)


# ── Profiles ──────────────────────────────────────────────────────────────────

@router.get("/profiles", response_model=list[UserAttendanceProfileRead])
def list_profiles(
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    profiles = (
        db.query(UserAttendanceProfile)
        .options(joinedload(UserAttendanceProfile.user), joinedload(UserAttendanceProfile.manager))
        .all()
    )
    result = []
    for p in profiles:
        data = UserAttendanceProfileRead.model_validate(p)
        if p.user:
            data.user_name = p.user.full_name
        if p.manager:
            data.manager_name = p.manager.full_name
        result.append(data)
    return result


@router.patch("/profiles/{user_id}", response_model=UserAttendanceProfileRead)
def update_profile(
    user_id: str,
    payload: UserAttendanceProfileUpdate,
    db: Session = Depends(get_db),
    _: User = _admin_only,
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    profile = svc.get_or_create_profile(db, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    p = (
        db.query(UserAttendanceProfile)
        .options(joinedload(UserAttendanceProfile.user), joinedload(UserAttendanceProfile.manager))
        .filter(UserAttendanceProfile.id == profile.id)
        .first()
    )
    data = UserAttendanceProfileRead.model_validate(p)
    if p.user:
        data.user_name = p.user.full_name
    if p.manager:
        data.manager_name = p.manager.full_name
    return data


# ── Corrections ───────────────────────────────────────────────────────────────

def _correction_read(correction: AttendanceCorrection) -> CorrectionRead:
    data = CorrectionRead.model_validate(correction)
    if correction.user:
        data.user_name = correction.user.full_name
    return data


def _can_review_correction(db: Session, reviewer: User, correction: AttendanceCorrection) -> bool:
    if reviewer.role == UserRole.admin:
        return True
    if reviewer.role != UserRole.sales_manager:
        return False
    profile = (
        db.query(UserAttendanceProfile)
        .filter(UserAttendanceProfile.user_id == correction.user_id)
        .first()
    )
    return profile is not None and profile.manager_id == reviewer.id


@router.get("/corrections", response_model=list[CorrectionRead])
def list_corrections_admin(
    status_filter: CorrectionStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in (UserRole.admin, UserRole.sales_manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    q = (
        db.query(AttendanceCorrection)
        .options(joinedload(AttendanceCorrection.user))
        .order_by(AttendanceCorrection.created_at.desc())
    )
    if status_filter:
        q = q.filter(AttendanceCorrection.status == status_filter)
    if current_user.role == UserRole.sales_manager:
        team_ids = [
            p.user_id
            for p in db.query(UserAttendanceProfile)
            .filter(UserAttendanceProfile.manager_id == current_user.id)
            .all()
        ]
        q = q.filter(AttendanceCorrection.user_id.in_(team_ids))
    return [_correction_read(c) for c in q.all()]


@router.patch("/corrections/{correction_id}", response_model=CorrectionRead)
def review_correction(
    correction_id: str,
    payload: CorrectionReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in (UserRole.admin, UserRole.sales_manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")
    correction = (
        db.query(AttendanceCorrection)
        .options(joinedload(AttendanceCorrection.user))
        .filter(AttendanceCorrection.id == correction_id)
        .first()
    )
    if not correction:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Correction not found.")
    if not _can_review_correction(db, current_user, correction):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot review this correction.")
    if payload.status == CorrectionStatus.approved:
        correction = svc.approve_correction(db, correction, current_user, payload.reviewer_notes)
    else:
        correction.status = CorrectionStatus.rejected
        correction.reviewer_id = current_user.id
        correction.reviewer_notes = payload.reviewer_notes
        correction.reviewed_at = datetime.utcnow()
        db.commit()
        db.refresh(correction)
    return _correction_read(correction)


# ── Team overview ───────────────────────────────────────────────────────────

@router.get("/team", response_model=list[TeamAttendanceSummary])
def team_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in (UserRole.admin, UserRole.sales_manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    users_q = db.query(User).filter(User.is_active.is_(True), User.role != UserRole.viewer)
    if current_user.role == UserRole.sales_manager:
        team_ids = [
            p.user_id
            for p in db.query(UserAttendanceProfile)
            .filter(UserAttendanceProfile.manager_id == current_user.id)
            .all()
        ]
        users_q = users_q.filter(User.id.in_(team_ids))

    users = users_q.all()
    today = work_date_for_user(db, current_user.id)
    summaries = []
    for user in users:
        session = (
            db.query(AttendanceSession)
            .filter(AttendanceSession.user_id == user.id, AttendanceSession.work_date == today)
            .first()
        )
        approved_leave = (
            db.query(LeaveApplication)
            .filter(
                LeaveApplication.user_id == user.id,
                LeaveApplication.status == LeaveStatus.approved,
                LeaveApplication.start_date <= today,
                LeaveApplication.end_date >= today,
            )
            .first()
        )
        leave_today = approved_leave or (
            db.query(LeaveApplication)
            .filter(
                LeaveApplication.user_id == user.id,
                LeaveApplication.status == LeaveStatus.pending,
                LeaveApplication.start_date <= today,
                LeaveApplication.end_date >= today,
            )
            .first()
        )
        on_leave = approved_leave is not None
        summaries.append(
            TeamAttendanceSummary(
                user_id=user.id,
                user_name=user.full_name,
                role=user.role.value,
                today_status=session.status if session else None,
                clock_in_at=session.clock_in_at if session else None,
                on_leave=on_leave,
                today_leave_status=leave_today.status if leave_today else None,
                today_leave_type=leave_today.leave_type if leave_today else None,
                today_is_half_day=leave_today.is_half_day if leave_today else False,
                today_half_day_period=leave_today.half_day_period if leave_today else None,
            )
        )
    return summaries
