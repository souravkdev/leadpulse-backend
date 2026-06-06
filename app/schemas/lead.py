from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr

from app.models.lead import LeadPriority, LeadSource, LeadStage
from app.schemas.user import UserReadBrief


class LeadCreate(BaseModel):
    title: str
    company_name: str | None = None
    contact_name: str
    email: EmailStr | None = None
    phone: str | None = None
    stage: LeadStage = LeadStage.new
    priority: LeadPriority = LeadPriority.medium
    source: LeadSource = LeadSource.other
    value: Decimal | None = None
    notes: str | None = None
    expected_close_date: date | None = None
    assigned_to_id: str | None = None


class LeadUpdate(BaseModel):
    title: str | None = None
    company_name: str | None = None
    contact_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    priority: LeadPriority | None = None
    source: LeadSource | None = None
    value: Decimal | None = None
    notes: str | None = None
    expected_close_date: date | None = None
    assigned_to_id: str | None = None


class LeadStageUpdate(BaseModel):
    stage: LeadStage


class LeadRead(BaseModel):
    id: str
    title: str
    company_name: str | None
    contact_name: str
    email: str | None
    phone: str | None
    stage: LeadStage
    priority: LeadPriority
    source: LeadSource
    value: Decimal | None
    notes: str | None
    expected_close_date: date | None
    assigned_to_id: str | None
    created_by_id: str
    created_at: datetime
    updated_at: datetime
    assignee: UserReadBrief | None = None
    creator: UserReadBrief | None = None

    model_config = {"from_attributes": True}


class LeadListResponse(BaseModel):
    items: list[LeadRead]
    total: int
    page: int
    page_size: int
    total_pages: int
