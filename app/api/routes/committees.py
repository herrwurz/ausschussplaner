"""API-Routen für Ausschüsse und Mitgliedschaften."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import require_staff
from app.db.base import get_db
from app.models.models import Ausschuss, Mitgliedschaft, Person, User
from app.schemas.schemas import (
    AusschussCreate,
    AusschussOut,
    AusschussUpdate,
    MitgliedOut,
)
from app.services.audit_service import write_audit

router = APIRouter(
    prefix="/committees",
    tags=["Ausschüsse"],
    dependencies=[Depends(require_staff)],
)


def _to_out(a: Ausschuss) -> AusschussOut:
    return AusschussOut(
        id=a.id,
        name=a.name,
        typ=a.typ,
        turnus=a.turnus,
        aktiv=a.aktiv,
        periode_id=a.periode_id,
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
def create_committee(
    payload: AusschussCreate,
    periode_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    a = Ausschuss(
        name=payload.name,
        typ=payload.typ,
        turnus=payload.turnus,
        aktiv=payload.aktiv,
        periode_id=periode_id,
    )
    db.add(a)
    db.flush()
    for m in payload.mitglieder:
        if db.get(Person, m.person_id) is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Person {m.person_id} fehlt")
        db.add(Mitgliedschaft(
            ausschuss_id=a.id,
            person_id=m.person_id,
            rolle=m.rolle,
            periode_id=periode_id,
        ))
    write_audit(
        db, user, action="ausschuss.anlegen", entity_type="ausschuss", entity_id=a.id,
        detail=a.name,
    )
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.get("/{committee_id}", response_model=AusschussOut)
def get_committee(committee_id: int, db: Session = Depends(get_db)):
    stmt = (
        select(Ausschuss)
        .where(Ausschuss.id == committee_id)
        .options(selectinload(Ausschuss.mitgliedschaften).selectinload(Mitgliedschaft.person))
    )
    a = db.scalars(stmt).first()
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ausschuss nicht gefunden")
    return _to_out(a)


@router.patch("/{committee_id}", response_model=AusschussOut)
def update_committee(
    committee_id: int,
    payload: AusschussUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
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
            db.add(Mitgliedschaft(
                ausschuss_id=a.id,
                person_id=m["person_id"],
                rolle=m["rolle"],
                periode_id=a.periode_id,
            ))
    note = a.name
    if mitglieder is not None:
        note = f"{a.name} (Mitgliedschaften: {len(mitglieder)})"
    write_audit(
        db, user, action="ausschuss.aendern", entity_type="ausschuss", entity_id=a.id,
        detail=note,
    )
    db.commit()
    db.refresh(a)
    return _to_out(a)


@router.post("/{committee_id}/copy-to-period", response_model=AusschussOut, status_code=status.HTTP_201_CREATED)
def copy_committee_to_period(
    committee_id: int,
    target_periode_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    """Kopiere Ausschuss zu neuer Periode (ohne Mitgliedschaften)."""
    from app.models.models import Gemeinderatsperiode

    source = db.get(Ausschuss, committee_id)
    if source is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Quell-Ausschuss nicht gefunden")

    periode = db.get(Gemeinderatsperiode, target_periode_id)
    if periode is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ziel-Periode nicht gefunden")

    if source.periode_id == target_periode_id:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Ziel-Periode ist identisch mit der Quell-Periode",
        )

    existing = db.scalars(
        select(Ausschuss).where(
            Ausschuss.periode_id == target_periode_id,
            Ausschuss.name == source.name,
        )
    ).first()
    if existing is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Ausschuss „{source.name}“ existiert bereits in der Ziel-Periode",
        )

    # Neue Instanz OHNE Mitgliedschaften (Admin setzt Besetzung manuell)
    new_committee = Ausschuss(
        name=source.name,
        typ=source.typ,
        turnus=f"{periode.start_jahr}-{periode.end_jahr}",
        aktiv=True,
        periode_id=target_periode_id,
    )
    db.add(new_committee)
    db.flush()
    write_audit(
        db, user, action="ausschuss.kopieren", entity_type="ausschuss", entity_id=new_committee.id,
        detail=f"{source.name} → Periode {target_periode_id}",
    )
    db.commit()
    db.refresh(new_committee)
    return _to_out(new_committee)


@router.delete("/{committee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_committee(
    committee_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    a = db.get(Ausschuss, committee_id)
    if a is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ausschuss nicht gefunden")
    write_audit(
        db, user, action="ausschuss.loeschen", entity_type="ausschuss", entity_id=a.id,
        detail=a.name,
    )
    db.delete(a)
    db.commit()
