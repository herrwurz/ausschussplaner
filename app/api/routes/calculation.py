"""API-Routen für Terminberechnung und Analyse."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.schemas import BerechnungRequest, BerechnungResponse, SitzungsvorschlagOut
from app.services.calculation_service import run_calculation, save_calculation_results

router = APIRouter(prefix="/calculate", tags=["Berechnung"])


@router.post("", response_model=BerechnungResponse)
def calculate(req: BerechnungRequest, db: Session = Depends(get_db)):
    """Berechnet Terminvorschläge (speichert NICHT automatisch)."""
    result = run_calculation(db, req)
    if not result.analysen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Keine aktiven Ausschüsse gefunden")
    # Nicht automatisch speichern! Nur über "Fixieren" Button speichern
    result.zusammenfassung["gespeicherte_vorschlaege"] = 0
    return result


@router.get("/results", response_model=list[SitzungsvorschlagOut])
def get_saved_results(db: Session = Depends(get_db)):
    """Gibt alle gespeicherten Sitzungsvorschläge zurück."""
    from app.models.models import Sitzungsvorschlag
    return db.query(Sitzungsvorschlag).all()


class SitzungsvorschlagCreate(BaseModel):
    """Speichere einen Sitzungsvorschlag."""
    ausschuss_id: int
    ausschuss_name: str | None = None
    woche: int
    wochentag: str
    start_minute: int
    end_minute: int


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
