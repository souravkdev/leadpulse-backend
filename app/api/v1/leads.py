import math

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from app.api.deps import get_current_active_user, get_db
from app.core.rbac import can_manage_lead
from app.models.lead import Lead, LeadStage
from app.models.user import User, UserRole
from app.schemas.activity import ActivityCreate, ActivityRead
from app.schemas.lead import (
    LeadCreate,
    LeadListResponse,
    LeadRead,
    LeadStageUpdate,
    LeadUpdate,
)
from app.models.activity import Activity

router = APIRouter(prefix="/leads", tags=["Leads"])


def _base_query(db: Session, current_user: User):
    """Return a base query filtered by role."""
    q = db.query(Lead).options(joinedload(Lead.assignee), joinedload(Lead.creator))
    if current_user.role == UserRole.sales_agent:
        q = q.filter(
            or_(
                Lead.assigned_to_id == current_user.id,
                Lead.created_by_id == current_user.id,
            )
        )
    return q


@router.get("/", response_model=LeadListResponse)
def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    stage: LeadStage | None = None,
    search: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    q = _base_query(db, current_user)

    if stage:
        q = q.filter(Lead.stage == stage)
    if search:
        term = f"%{search}%"
        q = q.filter(
            or_(
                Lead.title.ilike(term),
                Lead.contact_name.ilike(term),
                Lead.company_name.ilike(term),
                Lead.email.ilike(term),
            )
        )

    total = q.count()
    items = q.order_by(Lead.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return LeadListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.post("/", response_model=LeadRead, status_code=status.HTTP_201_CREATED)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewers cannot create leads.")

    lead = Lead(**payload.model_dump(), created_by_id=current_user.id)
    db.add(lead)
    db.commit()
    db.refresh(lead)
    # Reload with relationships
    db.expire(lead)
    return db.query(Lead).options(joinedload(Lead.assignee), joinedload(Lead.creator)).get(lead.id)


@router.get("/{lead_id}", response_model=LeadRead)
def get_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    lead = (
        db.query(Lead)
        .options(joinedload(Lead.assignee), joinedload(Lead.creator))
        .filter(Lead.id == lead_id)
        .first()
    )
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    if not can_manage_lead(current_user.role, current_user.id, lead.created_by_id):
        if current_user.role == UserRole.viewer:
            pass  # viewers can read any lead
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")
    return lead


@router.put("/{lead_id}", response_model=LeadRead)
def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    if not can_manage_lead(current_user.role, current_user.id, lead.created_by_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)

    db.commit()
    db.refresh(lead)
    db.expire(lead)
    return db.query(Lead).options(joinedload(Lead.assignee), joinedload(Lead.creator)).get(lead.id)


@router.patch("/{lead_id}/stage", response_model=LeadRead)
def update_lead_stage(
    lead_id: str,
    payload: LeadStageUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    if not can_manage_lead(current_user.role, current_user.id, lead.created_by_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied.")

    lead.stage = payload.stage
    db.commit()
    db.refresh(lead)
    db.expire(lead)
    return db.query(Lead).options(joinedload(Lead.assignee), joinedload(Lead.creator)).get(lead.id)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_lead(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role not in (UserRole.admin, UserRole.sales_manager):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only managers/admins can delete leads.")
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    db.delete(lead)
    db.commit()


# ── Activities sub-resource ──────────────────────────────────────────────────

@router.get("/{lead_id}/activities", response_model=list[ActivityRead])
def list_activities(
    lead_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")
    activities = (
        db.query(Activity)
        .options(joinedload(Activity.user))
        .filter(Activity.lead_id == lead_id)
        .order_by(Activity.created_at.desc())
        .all()
    )
    return activities


@router.post("/{lead_id}/activities", response_model=ActivityRead,
             status_code=status.HTTP_201_CREATED)
def create_activity(
    lead_id: str,
    payload: ActivityCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if current_user.role == UserRole.viewer:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Viewers cannot add activities.")
    lead = db.get(Lead, lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found.")

    activity = Activity(
        **payload.model_dump(),
        lead_id=lead_id,
        user_id=current_user.id,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    db.expire(activity)
    return db.query(Activity).options(joinedload(Activity.user)).get(activity.id)
