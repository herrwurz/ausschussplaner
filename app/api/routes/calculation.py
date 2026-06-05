"""API-Routen für Terminberechnung und Analyse."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.schemas import BerechnungRequest, BerechnungResponse, SitzungsvorschlagOut
from app.services.calculation_service import run_calculation, save_calculation_results

router = APIRouter(prefix="/calculate", tags=["Berechnung"])


@router.post("", response_model=BerechnungResponse)
def calculate(req: BerechnungRequest, db: Session = Depends(get_db)):
    """Berechnet Terminvorschläge für alle (oder gewählte) Ausschüsse und speichert sie."""
    result = run_calculation(db, req)
    if not result.analysen:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Keine aktiven Ausschüsse gefunden")
    saved = save_calculation_results(db, result)
    result.zusammenfassung["gespeicherte_vorschlaege"] = saved
    return result


@router.get("/results", response_model=list[SitzungsvorschlagOut])
def get_saved_results(db: Session = Depends(get_db)):
    """Gibt alle gespeicherten Sitzungsvorschläge zurück."""
    from app.models.models import Sitzungsvorschlag
    return db.query(Sitzungsvorschlag).all()
