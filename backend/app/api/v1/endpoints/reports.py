"""
Reports endpoint — deterministic Jinja2 + WeasyPrint PDFs (Pro / Business)
    POST /reports/template/fleet            — Fleet-wide PDF report
    POST /reports/template/driver/{driver_id} — Per-driver PDF report
"""

from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.schemas.report import TemplateReportRequest
from app.services import template_report_service

router = APIRouter(prefix="/reports", tags=["reports"])


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
