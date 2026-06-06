import uuid
import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class LeadStage(str, enum.Enum):
    new = "new"
    contacted = "contacted"
    qualified = "qualified"
    proposal = "proposal"
    negotiation = "negotiation"
    won = "won"
    lost = "lost"


class LeadPriority(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LeadSource(str, enum.Enum):
    website = "website"
    referral = "referral"
    cold_call = "cold_call"
    social_media = "social_media"
    email_campaign = "email_campaign"
    trade_show = "trade_show"
    other = "other"


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str | None] = mapped_column(String(255))
    contact_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    phone: Mapped[str | None] = mapped_column(String(50))
    stage: Mapped[LeadStage] = mapped_column(
        Enum(LeadStage), default=LeadStage.new, nullable=False, index=True
    )
    priority: Mapped[LeadPriority] = mapped_column(
        Enum(LeadPriority), default=LeadPriority.medium, nullable=False
    )
    source: Mapped[LeadSource] = mapped_column(
        Enum(LeadSource), default=LeadSource.other, nullable=False
    )
    value: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    notes: Mapped[str | None] = mapped_column(Text)
    expected_close_date: Mapped[date | None] = mapped_column(Date)

    # Relationships to users
    assigned_to_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    created_by_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    assignee: Mapped["User | None"] = relationship(  # noqa: F821
        "User", foreign_keys=[assigned_to_id], back_populates="assigned_leads"
    )
    creator: Mapped["User"] = relationship(  # noqa: F821
        "User", foreign_keys=[created_by_id], back_populates="created_leads"
    )
    activities: Mapped[list["Activity"]] = relationship(  # noqa: F821
        "Activity", back_populates="lead", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Lead {self.title} [{self.stage}]>"
