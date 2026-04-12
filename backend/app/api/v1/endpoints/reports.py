"""
Reports endpoint — Sprint 8
  US-032  POST /reports/generate  — On-demand AI fleet report (Pro / Business)
  US-033  GET  /reports/schedule  — Get schedule config
          PUT  /reports/schedule  — Enable/disable schedule + set frequency (Business)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.report import ReportGenerateResponse, ReportScheduleResponse, ReportScheduleUpdate
from app.services import ai_report_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportGenerateResponse)
def generate_report(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-032 — Trigger an on-demand AI fleet report. Delivered by email."""
    try:
        result = ai_report_service.generate_report_on_demand(
            db, owner.id, owner.email, owner.full_name
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return result


@router.get("/schedule", response_model=ReportScheduleResponse)
def get_schedule(
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-033 — Get the current scheduled report configuration."""
    sched = ai_report_service.get_schedule(db, owner.id)
    return sched


@router.put("/schedule", response_model=ReportScheduleResponse)
def update_schedule(
    body: ReportScheduleUpdate,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-033 — Enable/disable scheduled AI reports and set frequency (Business only)."""
    try:
        sched = ai_report_service.update_schedule(db, owner.id, body.enabled, body.frequency)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return sched
