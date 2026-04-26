"""
Export endpoint — Sprint 7
  US-031  POST /export  — Download fleet data as PDF / Excel
                          Supports: fuel, maintenance, analytics, activity_log
                          Requires Pro or Business plan.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_owner
from app.models.user import User
from app.services import export_service

router = APIRouter(tags=["export"])

_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MIME = "application/pdf"


@router.post("/export", response_model=None)
def export_data(
    format: Annotated[
        str, Query(description="Format de sortie : pdf | excel")
    ] = "excel",
    type: Annotated[
        str, Query(description="Type de données : fuel | maintenance")
    ] = "fuel",
    owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    """US-031 — Export fleet data as PDF or Excel (Pro / Business plan only)."""
    fmt = format.lower()
    data_type = type.lower()

    if fmt not in ("pdf", "excel"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Format invalide. Valeurs acceptées : pdf, excel",
        )
    if data_type not in ("fuel", "maintenance", "analytics", "activity_log"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type invalide. Valeurs acceptées : fuel, maintenance, analytics, activity_log",
        )

    if data_type == "fuel":
        if fmt == "excel":
            buf = export_service.generate_fuel_excel(db, owner.id)
            return StreamingResponse(
                buf,
                media_type=_EXCEL_MIME,
                headers={
                    "Content-Disposition": 'attachment; filename="carburant.xlsx"'
                },
            )
        buf = export_service.generate_fuel_pdf(db, owner.id, owner.full_name)
        return StreamingResponse(
            buf,
            media_type=_PDF_MIME,
            headers={"Content-Disposition": 'attachment; filename="carburant.pdf"'},
        )

    if data_type == "maintenance":
        if fmt == "excel":
            buf = export_service.generate_maintenance_excel(db, owner.id)
            return StreamingResponse(
                buf,
                media_type=_EXCEL_MIME,
                headers={
                    "Content-Disposition": 'attachment; filename="maintenance.xlsx"'
                },
            )
        buf = export_service.generate_maintenance_pdf(db, owner.id, owner.full_name)
        return StreamingResponse(
            buf,
            media_type=_PDF_MIME,
            headers={"Content-Disposition": 'attachment; filename="maintenance.pdf"'},
        )

    if data_type == "analytics":
        if fmt == "excel":
            buf = export_service.generate_analytics_excel(db, owner.id)
            return StreamingResponse(
                buf,
                media_type=_EXCEL_MIME,
                headers={
                    "Content-Disposition": 'attachment; filename="analytiques.xlsx"'
                },
            )
        buf = export_service.generate_analytics_pdf(db, owner.id, owner.full_name)
        return StreamingResponse(
            buf,
            media_type=_PDF_MIME,
            headers={"Content-Disposition": 'attachment; filename="analytiques.pdf"'},
        )

    # activity_log
    if fmt == "excel":
        buf = export_service.generate_activity_log_excel(db, owner.id)
        return StreamingResponse(
            buf,
            media_type=_EXCEL_MIME,
            headers={
                "Content-Disposition": 'attachment; filename="journal-activite.xlsx"'
            },
        )
    buf = export_service.generate_activity_log_pdf(db, owner.id, owner.full_name)
    return StreamingResponse(
        buf,
        media_type=_PDF_MIME,
        headers={"Content-Disposition": 'attachment; filename="journal-activite.pdf"'},
    )
