"""
Reports endpoint
  Sprint 8 — AI narrative reports
    US-032  POST /reports/generate  — On-demand AI fleet report (Pro / Business)
    US-033  GET  /reports/schedule  — Get schedule config
            PUT  /reports/schedule  — Enable/disable schedule + set frequency (Business)
  Template reports — deterministic Jinja2 + WeasyPrint PDFs (Pro / Business)
            POST /reports/template/fleet            — Fleet-wide PDF report
            POST /reports/template/driver/{driver_id} — Per-driver PDF report
"""

from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.report import (
    ReportGenerateResponse,
    ReportScheduleResponse,
    ReportScheduleUpdate,
    TemplateReportRequest,
)
from app.services import ai_report_service, template_report_service

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
        sched = ai_report_service.update_schedule(
            db, owner.id, body.enabled, body.frequency
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc))
    return sched


# ── Template reports (deterministic PDF) ─────────────────────────────────────


def _pdf_response(pdf_bytes: bytes, filename: str) -> StreamingResponse:
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/template/fleet")
def generate_fleet_template_report(
    body: TemplateReportRequest,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Generate a deterministic fleet-wide PDF report for the period."""
    pdf = template_report_service.render_fleet_pdf(
        owner, db, body.date_from, body.date_to
    )
    filename = f"rapport-flotte-{body.date_from}-{body.date_to}.pdf"
    return _pdf_response(pdf, filename)


@router.post("/template/driver/{driver_id}")
def generate_driver_template_report(
    driver_id: int,
    body: TemplateReportRequest,
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """Generate a deterministic per-driver PDF report for the period."""
    pdf = template_report_service.render_driver_pdf(
        owner, db, driver_id, body.date_from, body.date_to
    )
    filename = f"rapport-conducteur-{driver_id}-{body.date_from}-{body.date_to}.pdf"
    return _pdf_response(pdf, filename)
