import uuid
import enum
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class UserRole(str, enum.Enum):
    admin = "admin"
    sales_manager = "sales_manager"
    sales_agent = "sales_agent"
    viewer = "viewer"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole), default=UserRole.sales_agent, nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    assigned_leads: Mapped[list["Lead"]] = relationship(  # noqa: F821
        "Lead", foreign_keys="Lead.assigned_to_id", back_populates="assignee"
    )
    created_leads: Mapped[list["Lead"]] = relationship(  # noqa: F821
        "Lead", foreign_keys="Lead.created_by_id", back_populates="creator"
    )
    activities: Mapped[list["Activity"]] = relationship(  # noqa: F821
        "Activity", back_populates="user"
    )

    def __repr__(self) -> str:
        return f"<User {self.email} [{self.role}]>"
