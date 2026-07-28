"""API-Routen für Gemeinderatsperioden."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.base import get_db
from app.models.models import Gemeinderatsperiode
from app.schemas.schemas import PeriodeOut

router = APIRouter(
    prefix="/perioden",
    tags=["Perioden"],
    dependencies=[Depends(require_staff)],
)


class PeriodeCreate(BaseModel):
    name: str
    start_jahr: int
    end_jahr: int


@router.get("", response_model=list[PeriodeOut])
def list_perioden(db: Session = Depends(get_db)):
    """Liste alle Gemeinderatsperioden."""
    return db.query(Gemeinderatsperiode).order_by(Gemeinderatsperiode.start_jahr).all()


@router.post("", response_model=PeriodeOut, status_code=status.HTTP_201_CREATED)
def create_periode(payload: PeriodeCreate, db: Session = Depends(get_db)):
    """Erstelle eine neue Gemeinderatsperiode."""
    periode = Gemeinderatsperiode(
        name=payload.name,
        start_jahr=payload.start_jahr,
        end_jahr=payload.end_jahr,
        aktiv=True,
    )
    db.add(periode)
    db.commit()
    db.refresh(periode)
    return periode


@router.get("/{periode_id}", response_model=PeriodeOut)
def get_periode(periode_id: int, db: Session = Depends(get_db)):
    """Hole eine Gemeinderatsperiode."""
    periode = db.get(Gemeinderatsperiode, periode_id)
    if not periode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Periode nicht gefunden")
    return periode


class PeriodeUpdate(BaseModel):
    name: str | None = None
    start_jahr: int | None = None
    end_jahr: int | None = None
    aktiv: bool | None = None


@router.patch("/{periode_id}", response_model=PeriodeOut)
def update_periode(periode_id: int, payload: PeriodeUpdate, db: Session = Depends(get_db)):
    """Update eine Gemeinderatsperiode."""
    periode = db.get(Gemeinderatsperiode, periode_id)
    if not periode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Periode nicht gefunden")

    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(periode, k, v)
    db.commit()
    db.refresh(periode)
    return periode


@router.delete("/{periode_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_periode(periode_id: int, db: Session = Depends(get_db)):
    """Lösche eine Gemeinderatsperiode."""
    periode = db.get(Gemeinderatsperiode, periode_id)
    if not periode:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Periode nicht gefunden")
    db.delete(periode)
    db.commit()
