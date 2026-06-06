from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user, get_db
from app.models.lead import Lead, LeadStage
from app.models.user import User, UserRole

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return KPI metrics for the dashboard."""
    base = db.query(Lead)
    if current_user.role == UserRole.sales_agent:
        base = base.filter(Lead.created_by_id == current_user.id)

    total_leads = base.count()
    won = base.filter(Lead.stage == LeadStage.won).count()
    lost = base.filter(Lead.stage == LeadStage.lost).count()
    active = base.filter(Lead.stage.notin_([LeadStage.won, LeadStage.lost])).count()

    # Total pipeline value (active leads)
    pipeline_value = (
        base.filter(Lead.stage.notin_([LeadStage.won, LeadStage.lost]))
        .with_entities(func.sum(Lead.value))
        .scalar()
        or 0
    )
    won_value = (
        base.filter(Lead.stage == LeadStage.won)
        .with_entities(func.sum(Lead.value))
        .scalar()
        or 0
    )

    win_rate = round((won / (won + lost) * 100), 1) if (won + lost) > 0 else 0.0

    return {
        "total_leads": total_leads,
        "active_leads": active,
        "won_leads": won,
        "lost_leads": lost,
        "win_rate_percent": win_rate,
        "pipeline_value": float(pipeline_value),
        "won_value": float(won_value),
    }


@router.get("/pipeline")
def pipeline_breakdown(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return count and value per stage for pipeline view / charts."""
    base = db.query(Lead)
    if current_user.role == UserRole.sales_agent:
        base = base.filter(Lead.created_by_id == current_user.id)

    stages = db.query(
        Lead.stage,
        func.count(Lead.id).label("count"),
        func.sum(Lead.value).label("value"),
    )
    if current_user.role == UserRole.sales_agent:
        stages = stages.filter(Lead.created_by_id == current_user.id)

    results = stages.group_by(Lead.stage).all()

    stage_order = [s.value for s in LeadStage]
    breakdown = {s.value: {"count": 0, "value": 0.0} for s in LeadStage}
    for row in results:
        breakdown[row.stage.value] = {
            "count": row.count,
            "value": float(row.value or 0),
        }

    return {
        "stages": [
            {"stage": s, **breakdown[s]}
            for s in stage_order
        ]
    }
