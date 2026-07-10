import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AttendanceSessionStatus(str, enum.Enum):
    clocked_in = "clocked_in"
    on_break = "on_break"
    clocked_out = "clocked_out"


class BreakType(str, enum.Enum):
    short = "short"
    lunch = "lunch"
    other = "other"


class CorrectionStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class LeaveType(str, enum.Enum):
    paid = "paid"
    sick = "sick"
    unpaid = "unpaid"


class LeaveStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    cancelled = "cancelled"


class HalfDayPeriod(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"


class AttendanceSettings(Base):
    __tablename__ = "attendance_settings"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")
    work_week_days: Mapped[str] = mapped_column(
        String(32), nullable=False, default="0,1,2,3,4"
    )  # Mon-Fri as 0=Mon .. 6=Sun
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserAttendanceProfile(Base):
    __tablename__ = "user_attendance_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False
    )
    manager_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    timezone_override: Mapped[str | None] = mapped_column(String(64))
    attendance_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # noqa: F821
    manager: Mapped["User | None"] = relationship("User", foreign_keys=[manager_id])  # noqa: F821


class ShiftTemplate(Base):
    __tablename__ = "shift_templates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    end_time: Mapped[time] = mapped_column(Time, nullable=False)
    days_of_week: Mapped[str] = mapped_column(
        String(32), nullable=False, default="0,1,2,3,4"
    )
    lunch_break_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    short_break_minutes: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    short_break_limit: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    assignments: Mapped[list["ShiftAssignment"]] = relationship(
        "ShiftAssignment", back_populates="shift_template"
    )


class ShiftAssignment(Base):
    __tablename__ = "shift_assignments"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    shift_template_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("shift_templates.id", ondelete="CASCADE"), nullable=False
    )
    assignment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    shift_template: Mapped["ShiftTemplate"] = relationship(
        "ShiftTemplate", back_populates="assignments"
    )
    user: Mapped["User"] = relationship("User")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "assignment_date", name="uq_shift_user_date"),
    )


class AttendanceSession(Base):
    __tablename__ = "attendance_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[AttendanceSessionStatus] = mapped_column(
        Enum(AttendanceSessionStatus),
        default=AttendanceSessionStatus.clocked_in,
        nullable=False,
    )
    clock_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_break_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    shift_assignment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("shift_assignments.id", ondelete="SET NULL")
    )
    shift_warning: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    breaks: Mapped[list["BreakRecord"]] = relationship(
        "BreakRecord", back_populates="session", cascade="all, delete-orphan"
    )
    user: Mapped["User"] = relationship("User")  # noqa: F821




class BreakRecord(Base):
    __tablename__ = "break_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("attendance_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    break_type: Mapped[BreakType] = mapped_column(Enum(BreakType), nullable=False)
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    session: Mapped["AttendanceSession"] = relationship(
        "AttendanceSession", back_populates="breaks"
    )


class AttendanceCorrection(Base):
    __tablename__ = "attendance_corrections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("attendance_sessions.id", ondelete="SET NULL")
    )
    work_date: Mapped[date] = mapped_column(Date, nullable=False)
    original_clock_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    original_clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_clock_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    requested_clock_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[CorrectionStatus] = mapped_column(
        Enum(CorrectionStatus), default=CorrectionStatus.pending, nullable=False
    )
    reviewer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    reviewer_notes: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # noqa: F821
    reviewer: Mapped["User | None"] = relationship("User", foreign_keys=[reviewer_id])  # noqa: F821


class LeavePolicy(Base):
    __tablename__ = "leave_policies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False, unique=True)
    accrual_per_month: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class LeaveBalance(Base):
    __tablename__ = "leave_balances"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    accrued: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    used: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    carried_forward: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User")  # noqa: F821

    __table_args__ = (
        UniqueConstraint("user_id", "leave_type", name="uq_leave_balance_user_type"),
    )

    @property
    def balance(self) -> Decimal:
        return self.accrued + self.carried_forward - self.used


class LeaveApplication(Base):
    __tablename__ = "leave_applications"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    leave_type: Mapped[LeaveType] = mapped_column(Enum(LeaveType), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_half_day: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    half_day_period: Mapped[HalfDayPeriod | None] = mapped_column(Enum(HalfDayPeriod))
    days_requested: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[LeaveStatus] = mapped_column(
        Enum(LeaveStatus), default=LeaveStatus.pending, nullable=False, index=True
    )
    approver_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL")
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])  # noqa: F821
    approver: Mapped["User | None"] = relationship("User", foreign_keys=[approver_id])  # noqa: F821
