"""API-Routen für Jahresplan-Verwaltung."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.schemas import (
    JahresplanCopy,
    JahresplanCopyResult,
    JahresplanCreate,
    JahresplanOut,
)
from app.services.jahresplan_service import (
    copy_jahresplan,
    create_jahresplan,
    list_jahresplaene,
)

router = APIRouter(prefix="/jahresplan", tags=["Jahresplan"])


@router.get("", response_model=list[JahresplanOut])
def list_plans(db: Session = Depends(get_db)):
    return list_jahresplaene(db)


@router.post("", response_model=JahresplanOut, status_code=status.HTTP_201_CREATED)
def create_plan(payload: JahresplanCreate, db: Session = Depends(get_db)):
    return create_jahresplan(db, payload.jahr, payload.bezeichnung)


@router.post("/copy", response_model=JahresplanCopyResult)
def copy_plan(payload: JahresplanCopy, db: Session = Depends(get_db)):
    """Kopiert Stammdaten vom Quell- ins Zieljahr und erstellt einen neuen Jahresplan."""
    if payload.quelle_jahr == payload.ziel_jahr:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Quell- und Zieljahr müssen verschieden sein")
    try:
        return copy_jahresplan(db, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
