from datetime import datetime

from pydantic import BaseModel

from app.models.activity import ActivityType
from app.schemas.user import UserReadBrief


class ActivityCreate(BaseModel):
    type: ActivityType = ActivityType.note
    description: str
    due_date: datetime | None = None


class ActivityUpdate(BaseModel):
    description: str | None = None
    due_date: datetime | None = None
    completed_at: datetime | None = None


class ActivityRead(BaseModel):
    id: str
    lead_id: str
    user_id: str
    type: ActivityType
    description: str
    due_date: datetime | None
    completed_at: datetime | None
    created_at: datetime
    user: UserReadBrief | None = None

    model_config = {"from_attributes": True}
