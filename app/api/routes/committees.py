"""API-Routen für Ausschüsse und Mitgliedschaften."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.base import get_db
from app.models.models import Ausschuss, Mitgliedschaft, Person
from app.schemas.schemas import (
    AusschussCreate,
    AusschussOut,
    AusschussUpdate,
    MitgliedOut,
)

router = APIRouter(prefix="/committees", tags=["Ausschüsse"])


def _to_out(a: Ausschuss) -> AusschussOut:
    return AusschussOut(
        id=a.id,
        name=a.name,
        typ=a.typ,
        turnus=a.turnus,
        aktiv=a.aktiv,
        quorum_override=a.quorum_override,
        mitglieder=[
            MitgliedOut(person_id=ms.person_id, rolle=ms.rolle, name=ms.person.name)
            for ms in a.mitgliedschaften
            if ms.person is not None
        ],
    )


@router.get("", response_model=list[AusschussOut])
def list_committees(periode_id: int | None = None, db: Session = Depends(get_db)):
    """Liste Ausschüsse. Optional nach periode_id filtern."""
    stmt = select(Ausschuss).options(
        selectinload(Ausschuss.mitgliedschaften).selectinload(Mitgliedschaft.person)
    )
    if periode_id:
        stmt = stmt.where(Ausschuss.periode_id == periode_id)
    stmt = stmt.order_by(Ausschuss.name)
    return [_to_out(a) for a in db.scalars(stmt).unique().all()]


@router.post("", response_model=AusschussOut, status_code=status.HTTP_201_CREATED)
def create_committee(payload: AusschussCreate, periode_id: int | None = None, db: Session = Depends(get_db)):
    a = Ausschuss(
        name=payload.name,
        typ=payload.typ,
        turnus=payload.turnus,
        aktiv=payload.aktiv,
        periode_id=periode_id,
        quorum_override=payload.quorum_override,
    )
    db.add(a)
    db.flush()
    for m in payload.mitglieder:
        if db.get(Person, m.person_id) is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Person {m.person_id} fehlt")
        db.add(Mitgliedschaft(ausschuss_id=a.id, person_id=m.person_id, rolle=m.rolle))
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.get("/{committee_id}", response_model=AusschussOut)
def get_committee(committee_id: int, db: Session = Depends(get_db)):
    a = db.get(Ausschuss, committee_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ausschuss nicht gefunden")
    return _to_out(a)


@router.patch("/{committee_id}", response_model=AusschussOut)
def update_committee(committee_id: int, payload: AusschussUpdate, db: Session = Depends(get_db)):
    a = db.get(Ausschuss, committee_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ausschuss nicht gefunden")
    data = payload.model_dump(exclude_unset=True)
    mitglieder = data.pop("mitglieder", None)
    for k, v in data.items():
        setattr(a, k, v)
    if mitglieder is not None:
        db.query(Mitgliedschaft).filter(Mitgliedschaft.ausschuss_id == a.id).delete()
        for m in mitglieder:
            db.add(Mitgliedschaft(ausschuss_id=a.id, person_id=m["person_id"], rolle=m["rolle"]))
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.post("/{committee_id}/copy-to-period", response_model=AusschussOut, status_code=status.HTTP_201_CREATED)
def copy_committee_to_period(committee_id: int, target_periode_id: int, db: Session = Depends(get_db)):
    """Kopiere Ausschuss zu neuer Periode (ohne Mitgliedschaften)."""
    source = db.get(Ausschuss, committee_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quell-Ausschuss nicht gefunden")

    # Überprüfe, ob Periode existiert
    from app.models.models import Jahresplan
    periode = db.get(Jahresplan, target_periode_id)
    if periode is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ziel-Periode nicht gefunden")

    # Erstelle neuen Ausschuss OHNE Mitgliedschaften
    new_committee = Ausschuss(
        name=source.name,
        typ=source.typ,
        turnus=str(periode.jahr),  # turnus = Jahr der Periode
        aktiv=True,
        periode_id=target_periode_id,
        quorum_override=source.quorum_override,
    )
    db.add(new_committee)
    db.commit()
    db.refresh(new_committee)
    return _to_out(new_committee)


@router.delete("/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_committee(committee_id: int, db: Session = Depends(get_db)):
    a = db.get(Ausschuss, committee_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ausschuss nicht gefunden")
    db.delete(a)
    db.commit()
