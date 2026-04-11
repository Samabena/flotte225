"""
Export endpoint — Sprint 7
  US-031  POST /export  — Download fuel or maintenance data as PDF / Excel
                          Requires Pro or Business plan.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_plan
from app.models.user import User
from app.services import export_service

router = APIRouter(tags=["export"])

_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
_PDF_MIME = "application/pdf"


@router.post("/export", response_model=None)
def export_data(
    format: Annotated[str, Query(description="Format de sortie : pdf | excel")] = "excel",
    type: Annotated[str, Query(description="Type de données : fuel | maintenance")] = "fuel",
    owner: User = Depends(require_plan("pro", "business")),
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
    if data_type not in ("fuel", "maintenance"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Type invalide. Valeurs acceptées : fuel, maintenance",
        )

    if data_type == "fuel":
        if fmt == "excel":
            buf = export_service.generate_fuel_excel(db, owner.id)
            return StreamingResponse(
                buf,
                media_type=_EXCEL_MIME,
                headers={"Content-Disposition": 'attachment; filename="carburant.xlsx"'},
            )
        buf = export_service.generate_fuel_pdf(db, owner.id, owner.full_name)
        return StreamingResponse(
            buf,
            media_type=_PDF_MIME,
            headers={"Content-Disposition": 'attachment; filename="carburant.pdf"'},
        )

    # maintenance
    if fmt == "excel":
        buf = export_service.generate_maintenance_excel(db, owner.id)
        return StreamingResponse(
            buf,
            media_type=_EXCEL_MIME,
            headers={"Content-Disposition": 'attachment; filename="maintenance.xlsx"'},
        )
    buf = export_service.generate_maintenance_pdf(db, owner.id, owner.full_name)
    return StreamingResponse(
        buf,
        media_type=_PDF_MIME,
        headers={"Content-Disposition": 'attachment; filename="maintenance.pdf"'},
    )
