from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user, get_db
from app.core.rbac import can_approve_leave, can_use_attendance
from app.models.attendance import LeaveApplication, LeaveStatus, LeaveType, UserAttendanceProfile
from app.models.user import User, UserRole
from app.schemas.attendance import (
    LeaveApplicationCreate,
    LeaveApplicationRead,
    LeaveBalanceRead,
    LeaveRejectRequest,
)
from app.services import attendance_service as svc

router = APIRouter(prefix="/leave", tags=["Leave"])


def _balance_read(balance) -> LeaveBalanceRead:
    return LeaveBalanceRead(
        leave_type=balance.leave_type,
        accrued=balance.accrued,
        used=balance.used,
        carried_forward=balance.carried_forward,
        balance=balance.balance,
    )


def _app_read(app: LeaveApplication) -> LeaveApplicationRead:
    data = LeaveApplicationRead.model_validate(app)
    if app.user:
        data.user_name = app.user.full_name
    return data


@router.get("/balances", response_model=list[LeaveBalanceRead])
def get_balances(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not can_use_attendance(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Leave not available.")
    from app.models.attendance import LeaveType

    balances = []
    for lt in LeaveType:
        if lt == LeaveType.unpaid:
            continue
        bal = svc.get_leave_balance(db, current_user.id, lt)
        balances.append(_balance_read(bal))
    return balances


@router.get("/applications", response_model=list[LeaveApplicationRead])
def list_applications(
    status_filter: LeaveStatus | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not can_use_attendance(current_user.role):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Leave not available.")

    q = (
        db.query(LeaveApplication)
        .options(joinedload(LeaveApplication.user))
        .filter(LeaveApplication.user_id == current_user.id)
        .order_by(LeaveApplication.created_at.desc())
    )
    if status_filter:
        q = q.filter(LeaveApplication.status == status_filter)
    return [_app_read(a) for a in q.all()]


@router.post("/applications", response_model=LeaveApplicationRead, status_code=status.HTTP_201_CREATED)
def apply_leave(
    payload: LeaveApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    svc.ensure_attendance_access(current_user)
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End date must be on or after start date.")
    if payload.is_half_day and payload.start_date != payload.end_date:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Half-day leave must be a single day.")
    if payload.is_half_day and not payload.half_day_period:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Half-day period required.")

    if svc.has_overlapping_leave(db, current_user.id, payload.start_date, payload.end_date):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Overlapping leave application exists.")

    days = svc.count_leave_days(payload.start_date, payload.end_date, payload.is_half_day)
    if payload.leave_type != LeaveType.unpaid:
        balance = svc.get_leave_balance(db, current_user.id, payload.leave_type)
        if balance.balance < days:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient balance. Available: {balance.balance}, requested: {days}",
            )

    application = LeaveApplication(
        user_id=current_user.id,
        leave_type=payload.leave_type,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_half_day=payload.is_half_day,
        half_day_period=payload.half_day_period,
        days_requested=days,
        reason=payload.reason,
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    app = (
        db.query(LeaveApplication)
        .options(joinedload(LeaveApplication.user))
        .filter(LeaveApplication.id == application.id)
        .first()
    )
    return _app_read(app)


@router.patch("/applications/{application_id}/cancel", response_model=LeaveApplicationRead)
def cancel_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    app = db.get(LeaveApplication, application_id)
    if not app or app.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    if app.status != LeaveStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only pending applications can be cancelled.")
    app.status = LeaveStatus.cancelled
    db.commit()
    db.refresh(app)
    return _app_read(app)


@router.patch("/applications/{application_id}/approve", response_model=LeaveApplicationRead)
def approve_application(
    application_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    app = (
        db.query(LeaveApplication)
        .options(joinedload(LeaveApplication.user))
        .filter(LeaveApplication.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    if app.status != LeaveStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application is not pending.")

    profile = (
        db.query(UserAttendanceProfile)
        .filter(UserAttendanceProfile.user_id == app.user_id)
        .first()
    )
    manager_id = profile.manager_id if profile else None
    if not can_approve_leave(current_user.role, current_user.id, manager_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot approve this application.")

    balance = svc.get_leave_balance(db, app.user_id, app.leave_type)
    if app.leave_type != LeaveType.unpaid:
        if balance.balance < app.days_requested:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Insufficient leave balance.")

    app.status = LeaveStatus.approved
    app.approver_id = current_user.id
    from datetime import datetime

    app.reviewed_at = datetime.utcnow()
    if app.leave_type != LeaveType.unpaid:
        balance.used += app.days_requested
    db.commit()
    db.refresh(app)
    return _app_read(app)


@router.patch("/applications/{application_id}/reject", response_model=LeaveApplicationRead)
def reject_application(
    application_id: str,
    payload: LeaveRejectRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    app = (
        db.query(LeaveApplication)
        .options(joinedload(LeaveApplication.user))
        .filter(LeaveApplication.id == application_id)
        .first()
    )
    if not app:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found.")
    if app.status != LeaveStatus.pending:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Application is not pending.")

    profile = (
        db.query(UserAttendanceProfile)
        .filter(UserAttendanceProfile.user_id == app.user_id)
        .first()
    )
    manager_id = profile.manager_id if profile else None
    if not can_approve_leave(current_user.role, current_user.id, manager_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot reject this application.")

    app.status = LeaveStatus.rejected
    app.approver_id = current_user.id
    app.rejection_reason = payload.rejection_reason
    from datetime import datetime

    app.reviewed_at = datetime.utcnow()
    db.commit()
    db.refresh(app)
    return _app_read(app)


@router.get("/applications/pending", response_model=list[LeaveApplicationRead])
def list_pending_for_approval(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in (UserRole.admin, UserRole.sales_manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    q = (
        db.query(LeaveApplication)
        .options(joinedload(LeaveApplication.user))
        .filter(LeaveApplication.status == LeaveStatus.pending)
        .order_by(LeaveApplication.created_at.asc())
    )
    if current_user.role == UserRole.sales_manager:
        team_ids = [
            p.user_id
            for p in db.query(UserAttendanceProfile)
            .filter(UserAttendanceProfile.manager_id == current_user.id)
            .all()
        ]
        q = q.filter(LeaveApplication.user_id.in_(team_ids))

    return [_app_read(a) for a in q.all()]
