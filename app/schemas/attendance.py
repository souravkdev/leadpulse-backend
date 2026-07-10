from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.attendance import (
    AttendanceSessionStatus,
    BreakType,
    CorrectionStatus,
    HalfDayPeriod,
    LeaveStatus,
    LeaveType,
)


# ── Attendance ────────────────────────────────────────────────────────────────

class BreakRecordRead(BaseModel):
    id: str
    break_type: BreakType
    start_at: datetime
    end_at: datetime | None
    duration_minutes: int | None

    model_config = {"from_attributes": True}


class AttendanceSessionRead(BaseModel):
    id: str
    work_date: date
    status: AttendanceSessionStatus
    clock_in_at: datetime
    clock_out_at: datetime | None
    total_break_minutes: int
    shift_warning: bool
    breaks: list[BreakRecordRead] = []

    model_config = {"from_attributes": True}


class TodayAttendanceResponse(BaseModel):
    session: AttendanceSessionRead | None
    shift_warning: bool = False
    shift_name: str | None = None
    shift_start_time: time | None = None
    shift_end_time: time | None = None
    elapsed_work_minutes: int = 0
    elapsed_break_minutes: int = 0
    active_break: BreakRecordRead | None = None
    lunch_breaks_taken: int = 0
    lunch_break_minutes: int = 30
    short_break_minutes: int = 15


class BreakStartRequest(BaseModel):
    break_type: BreakType


class CalendarDayEntry(BaseModel):
    date: date
    session: AttendanceSessionRead | None = None
    on_leave: bool = False
    leave_type: LeaveType | None = None
    is_half_day: bool = False
    has_missing_clock_out: bool = False


class DaySessionDetail(BaseModel):
    id: str
    clock_in_at: datetime
    clock_out_at: datetime | None
    status: AttendanceSessionStatus
    breaks: list[BreakRecordRead] = []
    work_minutes: int = 0
    break_minutes: int = 0
    missing_clock_out: bool = False
    pending_correction_id: str | None = None


class DayAttendanceDetail(BaseModel):
    date: date
    on_leave: bool = False
    leave_type: LeaveType | None = None
    is_half_day: bool = False
    half_day_period: HalfDayPeriod | None = None
    sessions: list[DaySessionDetail] = []
    total_work_minutes: int = 0
    total_break_minutes: int = 0
    has_missing_clock_out: bool = False


class CalendarResponse(BaseModel):
    month: str
    days: list[CalendarDayEntry]


class AttendanceSessionListResponse(BaseModel):
    items: list[AttendanceSessionRead]
    total: int
    page: int
    page_size: int


class CorrectionCreate(BaseModel):
    work_date: date
    session_id: str | None = None
    requested_clock_in_at: datetime | None = None
    requested_clock_out_at: datetime | None = None
    reason: str = Field(min_length=3)


class CorrectionRead(BaseModel):
    id: str
    work_date: date
    session_id: str | None
    original_clock_in_at: datetime | None
    original_clock_out_at: datetime | None
    requested_clock_in_at: datetime | None
    requested_clock_out_at: datetime | None
    reason: str
    status: CorrectionStatus
    reviewer_notes: str | None
    reviewed_at: datetime | None
    created_at: datetime
    user_name: str | None = None

    model_config = {"from_attributes": True}


class CorrectionReview(BaseModel):
    status: CorrectionStatus
    reviewer_notes: str | None = None


# ── Leave ─────────────────────────────────────────────────────────────────────

class LeaveBalanceRead(BaseModel):
    leave_type: LeaveType
    accrued: Decimal
    used: Decimal
    carried_forward: Decimal
    balance: Decimal


class LeaveApplicationCreate(BaseModel):
    leave_type: LeaveType
    start_date: date
    end_date: date
    is_half_day: bool = False
    half_day_period: HalfDayPeriod | None = None
    reason: str = Field(min_length=3)


class LeaveApplicationRead(BaseModel):
    id: str
    leave_type: LeaveType
    start_date: date
    end_date: date
    is_half_day: bool
    half_day_period: HalfDayPeriod | None
    days_requested: Decimal
    reason: str
    status: LeaveStatus
    approver_id: str | None
    rejection_reason: str | None
    reviewed_at: datetime | None
    created_at: datetime
    user_id: str
    user_name: str | None = None

    model_config = {"from_attributes": True}


class LeaveRejectRequest(BaseModel):
    rejection_reason: str = Field(min_length=3)


# ── Admin ─────────────────────────────────────────────────────────────────────

class ShiftTemplateCreate(BaseModel):
    name: str
    start_time: time
    end_time: time
    days_of_week: str = "0,1,2,3,4"
    lunch_break_minutes: int = 30
    short_break_minutes: int = 15
    short_break_limit: int | None = None


class ShiftTemplateRead(BaseModel):
    id: str
    name: str
    start_time: time
    end_time: time
    days_of_week: str
    lunch_break_minutes: int
    short_break_minutes: int
    short_break_limit: int
    is_active: bool

    model_config = {"from_attributes": True}


class ShiftAssignmentCreate(BaseModel):
    user_id: str
    shift_template_id: str
    start_date: date | None = None
    end_date: date | None = None


class ShiftAssignmentBulkResponse(BaseModel):
    user_id: str
    shift_template_id: str
    start_date: date
    end_date: date
    days_assigned: int


class ShiftAssignmentSummary(BaseModel):
    user_id: str
    user_name: str | None
    shift_template_id: str
    shift_name: str | None
    start_date: date
    end_date: date
    days_count: int


class ShiftAssignmentDeleteResponse(BaseModel):
    deleted: int


class ShiftAssignmentRead(BaseModel):
    id: str
    user_id: str
    shift_template_id: str
    assignment_date: date
    shift_template: ShiftTemplateRead | None = None
    user_name: str | None = None

    model_config = {"from_attributes": True}


class LeavePolicyCreate(BaseModel):
    leave_type: LeaveType
    accrual_per_month: Decimal = Field(gt=0)
    is_active: bool = True


class LeavePolicyUpdate(BaseModel):
    accrual_per_month: Decimal | None = None
    is_active: bool | None = None


class LeavePolicyRead(BaseModel):
    id: str
    leave_type: LeaveType
    accrual_per_month: Decimal
    is_active: bool

    model_config = {"from_attributes": True}


class UserAttendanceProfileUpdate(BaseModel):
    manager_id: str | None = None
    timezone_override: str | None = None
    attendance_enabled: bool | None = None


class UserAttendanceProfileRead(BaseModel):
    id: str
    user_id: str
    manager_id: str | None
    timezone_override: str | None
    attendance_enabled: bool
    user_name: str | None = None
    manager_name: str | None = None

    model_config = {"from_attributes": True}


class TeamAttendanceSummary(BaseModel):
    user_id: str
    user_name: str
    role: str
    today_status: AttendanceSessionStatus | None
    clock_in_at: datetime | None
    on_leave: bool = False
    today_leave_status: LeaveStatus | None = None
    today_leave_type: LeaveType | None = None
    today_is_half_day: bool = False
    today_half_day_period: HalfDayPeriod | None = None
