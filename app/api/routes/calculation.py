"""API-Routen für Terminberechnung und Analyse."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.base import get_db
from app.schemas.schemas import BerechnungRequest, BerechnungResponse, SitzungsvorschlagOut
from app.services.calculation_service import run_calculation, save_calculation_results
from app.services.pdf_service import (
    PlanTermin,
    build_wochenplan_pdf,
    load_ausschuss_namen,
    parse_time_to_minutes,
    parse_wochentag,
    vorschlaege_to_plan,
)

router = APIRouter(
    prefix="/calculate",
    tags=["Berechnung"],
    dependencies=[Depends(require_staff)],
)


@router.post("", response_model=BerechnungResponse)
def calculate(req: BerechnungRequest, db: Session = Depends(get_db)):
    """Berechnet Terminvorschläge (speichert NICHT automatisch)."""
    result = run_calculation(db, req)
    if not result.analysen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Keine aktiven Ausschüsse gefunden")
    return result


@router.get("/results", response_model=list[SitzungsvorschlagOut])
def get_saved_results(db: Session = Depends(get_db)):
    """Gibt alle gespeicherten Sitzungsvorschläge zurück."""
    from app.models.models import Sitzungsvorschlag
    return db.query(Sitzungsvorschlag).all()


@router.get("/results/pdf")
def export_results_pdf(db: Session = Depends(get_db)):
    """PDF-Wochenplan aller fixierten Sitzungstermine."""
    from app.models.models import Sitzungsvorschlag

    rows = (
        db.query(Sitzungsvorschlag)
        .order_by(Sitzungsvorschlag.woche, Sitzungsvorschlag.wochentag, Sitzungsvorschlag.start_minute)
        .all()
    )
    namen = load_ausschuss_namen(db, {r.ausschuss_id for r in rows})
    untertitel = None
    anchors = {r.planungs_start_datum for r in rows if r.planungs_start_datum}
    start_datum = next(iter(anchors)) if len(anchors) == 1 else None
    if start_datum is not None:
        untertitel = f"Planungsstart: {start_datum.strftime('%d.%m.%Y')}"
    elif anchors:
        untertitel = "Mehrere Planungsstarts – relative Wochenanzeige"

    pdf_bytes = build_wochenplan_pdf(
        vorschlaege_to_plan(rows, namen),
        titel="Sitzungsplan Ausschüsse",
        untertitel=untertitel,
        start_datum=start_datum,
    )
    filename = f"sitzungsplan_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class WochenplanPdfItem(BaseModel):
    ausschuss_id: int
    ausschuss_name: str
    woche: int
    wochentag: str
    start: str
    ende: str
    quote: int | None = None


class WochenplanPdfRequest(BaseModel):
    """Aktueller Berechnungs-Wochenplan (noch nicht zwingend fixiert)."""

    titel: str | None = None
    start_datum: date | None = None
    termine: list[WochenplanPdfItem]


@router.post("/pdf")
def export_wochenplan_pdf(payload: WochenplanPdfRequest):
    """PDF aus dem aktuell angezeigten Wochenplan (Berechnungsergebnis)."""
    if not payload.termine:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Keine Termine zum Exportieren")

    plan: list[PlanTermin] = []
    for item in payload.termine:
        try:
            plan.append(
                PlanTermin(
                    ausschuss_id=item.ausschuss_id,
                    ausschuss_name=item.ausschuss_name,
                    woche=item.woche,
                    wochentag=parse_wochentag(item.wochentag),
                    start_minute=parse_time_to_minutes(item.start),
                    end_minute=parse_time_to_minutes(item.ende),
                    quote=item.quote,
                )
            )
        except (KeyError, ValueError, IndexError) as err:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                f"Ungültiger Termin: {item.ausschuss_name} ({err})",
            ) from err

    untertitel = None
    if payload.start_datum:
        untertitel = f"Planungsstart: {payload.start_datum.strftime('%d.%m.%Y')}"

    pdf_bytes = build_wochenplan_pdf(
        plan,
        titel=payload.titel or "Sitzungsplan Ausschüsse",
        untertitel=untertitel,
        start_datum=payload.start_datum,
    )
    filename = f"wochenplan_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


class SitzungsvorschlagCreate(BaseModel):
    """Speichere einen Sitzungsvorschlag."""
    ausschuss_id: int
    ausschuss_name: str | None = None
    woche: int
    wochentag: str
    start_minute: int
    end_minute: int
    planungs_start_datum: date | None = None


@router.post("/results", response_model=SitzungsvorschlagOut, status_code=status.HTTP_201_CREATED)
def create_sitzungsvorschlag(payload: SitzungsvorschlagCreate, db: Session = Depends(get_db)):
    """Speichere einen einzelnen Sitzungsvorschlag."""
    from app.models.models import Sitzungsvorschlag
    from app.models.enums import Wochentag, TerminStatus

    try:
        vorschlag = Sitzungsvorschlag(
            ausschuss_id=payload.ausschuss_id,
            woche=payload.woche,
            wochentag=Wochentag[payload.wochentag.upper()],
            start_minute=payload.start_minute,
            end_minute=payload.end_minute,
            anwesend_count=0,
            mitglieder_count=0,
            quote=0,
            obmann_da=False,
            stv_da=False,
            status=TerminStatus.TOP,
            fehlende='',
            planungs_start_datum=payload.planungs_start_datum,
        )
        db.add(vorschlag)
        db.commit()
        db.refresh(vorschlag)
        return vorschlag
    except Exception as err:
        db.rollback()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(err))


@router.delete("/results/{vorschlag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sitzungsvorschlag(vorschlag_id: int, db: Session = Depends(get_db)):
    """Lösche einen Sitzungsvorschlag."""
    from app.models.models import Sitzungsvorschlag

    vorschlag = db.get(Sitzungsvorschlag, vorschlag_id)
    if not vorschlag:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Sitzungsvorschlag nicht gefunden")

    db.delete(vorschlag)
    db.commit()
