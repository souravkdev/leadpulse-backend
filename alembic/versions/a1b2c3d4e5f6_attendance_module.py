"""attendance_module

Revision ID: a1b2c3d4e5f6
Revises: 0fc932bde3bc
Create Date: 2026-07-10 22:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "0fc932bde3bc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

attendance_session_status = postgresql.ENUM(
    "clocked_in", "on_break", "clocked_out", name="attendancesessionstatus", create_type=False
)
break_type = postgresql.ENUM("short", "lunch", "other", name="breaktype", create_type=False)
correction_status = postgresql.ENUM(
    "pending", "approved", "rejected", name="correctionstatus", create_type=False
)
leave_type = postgresql.ENUM("paid", "sick", "unpaid", name="leavetype", create_type=False)
leave_status = postgresql.ENUM(
    "pending", "approved", "rejected", "cancelled", name="leavestatus", create_type=False
)
half_day_period = postgresql.ENUM("morning", "afternoon", name="halfdayperiod", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    attendance_session_status.create(bind, checkfirst=True)
    break_type.create(bind, checkfirst=True)
    correction_status.create(bind, checkfirst=True)
    leave_type.create(bind, checkfirst=True)
    leave_status.create(bind, checkfirst=True)
    half_day_period.create(bind, checkfirst=True)

    op.create_table(
        "attendance_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("company_timezone", sa.String(length=64), nullable=False),
        sa.Column("work_week_days", sa.String(length=32), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "shift_templates",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("days_of_week", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "leave_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("leave_type", leave_type, nullable=False),
        sa.Column("accrual_per_month", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("leave_type"),
    )
    op.create_table(
        "user_attendance_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("manager_id", sa.String(length=36), nullable=True),
        sa.Column("timezone_override", sa.String(length=64), nullable=True),
        sa.Column("attendance_enabled", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["manager_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "shift_assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("shift_template_id", sa.String(length=36), nullable=False),
        sa.Column("assignment_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["shift_template_id"], ["shift_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "assignment_date", name="uq_shift_user_date"),
    )
    op.create_index(op.f("ix_shift_assignments_assignment_date"), "shift_assignments", ["assignment_date"], unique=False)
    op.create_index(op.f("ix_shift_assignments_user_id"), "shift_assignments", ["user_id"], unique=False)
    op.create_table(
        "leave_balances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("leave_type", leave_type, nullable=False),
        sa.Column("accrued", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("used", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("carried_forward", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "leave_type", name="uq_leave_balance_user_type"),
    )
    op.create_index(op.f("ix_leave_balances_user_id"), "leave_balances", ["user_id"], unique=False)
    op.create_table(
        "leave_applications",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("leave_type", leave_type, nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("is_half_day", sa.Boolean(), nullable=False),
        sa.Column("half_day_period", half_day_period, nullable=True),
        sa.Column("days_requested", sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", leave_status, nullable=False),
        sa.Column("approver_id", sa.String(length=36), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["approver_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_leave_applications_status"), "leave_applications", ["status"], unique=False)
    op.create_index(op.f("ix_leave_applications_user_id"), "leave_applications", ["user_id"], unique=False)
    op.create_table(
        "attendance_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("status", attendance_session_status, nullable=False),
        sa.Column("clock_in_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("clock_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_break_minutes", sa.Integer(), nullable=False),
        sa.Column("shift_assignment_id", sa.String(length=36), nullable=True),
        sa.Column("shift_warning", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["shift_assignment_id"], ["shift_assignments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "work_date", name="uq_attendance_user_work_date"),
    )
    op.create_index(op.f("ix_attendance_sessions_user_id"), "attendance_sessions", ["user_id"], unique=False)
    op.create_index(op.f("ix_attendance_sessions_work_date"), "attendance_sessions", ["work_date"], unique=False)
    op.create_table(
        "attendance_corrections",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("original_clock_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("original_clock_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_clock_in_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_clock_out_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", correction_status, nullable=False),
        sa.Column("reviewer_id", sa.String(length=36), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["reviewer_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["session_id"], ["attendance_sessions.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_attendance_corrections_user_id"), "attendance_corrections", ["user_id"], unique=False)
    op.create_table(
        "break_records",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("break_type", break_type, nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["attendance_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_break_records_session_id"), "break_records", ["session_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_break_records_session_id"), table_name="break_records")
    op.drop_table("break_records")
    op.drop_index(op.f("ix_attendance_corrections_user_id"), table_name="attendance_corrections")
    op.drop_table("attendance_corrections")
    op.drop_index(op.f("ix_attendance_sessions_work_date"), table_name="attendance_sessions")
    op.drop_index(op.f("ix_attendance_sessions_user_id"), table_name="attendance_sessions")
    op.drop_table("attendance_sessions")
    op.drop_index(op.f("ix_leave_applications_user_id"), table_name="leave_applications")
    op.drop_index(op.f("ix_leave_applications_status"), table_name="leave_applications")
    op.drop_table("leave_applications")
    op.drop_index(op.f("ix_leave_balances_user_id"), table_name="leave_balances")
    op.drop_table("leave_balances")
    op.drop_index(op.f("ix_shift_assignments_user_id"), table_name="shift_assignments")
    op.drop_index(op.f("ix_shift_assignments_assignment_date"), table_name="shift_assignments")
    op.drop_table("shift_assignments")
    op.drop_table("user_attendance_profiles")
    op.drop_table("leave_policies")
    op.drop_table("shift_templates")
    op.drop_table("attendance_settings")

    bind = op.get_bind()
    half_day_period.drop(bind, checkfirst=True)
    leave_status.drop(bind, checkfirst=True)
    leave_type.drop(bind, checkfirst=True)
    correction_status.drop(bind, checkfirst=True)
    break_type.drop(bind, checkfirst=True)
    attendance_session_status.drop(bind, checkfirst=True)
