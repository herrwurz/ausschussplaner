"""API-Routen für Abwesenheiten."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.base import get_db
from app.models.models import Abwesenheit, Person, User
from app.schemas.schemas import AbwesenheitCreate, AbwesenheitOut
from app.services.audit_service import write_audit

router = APIRouter(
    prefix="/absences",
    tags=["Abwesenheiten"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=list[AbwesenheitOut])
def list_absences(person_id: int | None = None, db: Session = Depends(get_db)):
    stmt = select(Abwesenheit)
    if person_id:
        stmt = stmt.where(Abwesenheit.person_id == person_id)
    result = []
    for ab in db.scalars(stmt.order_by(Abwesenheit.von)).all():
        out = AbwesenheitOut.model_validate(ab)
        out.person_name = ab.person.name if ab.person else None
        result.append(out)
    return result


@router.post("", response_model=AbwesenheitOut, status_code=status.HTTP_201_CREATED)
def create_absence(
    payload: AbwesenheitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    person = db.get(Person, payload.person_id)
    if person is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Person fehlt")
    if payload.bis < payload.von:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bis vor von")
    ab = Abwesenheit(**payload.model_dump())
    db.add(ab)
    db.flush()
    write_audit(
        db, user, action="abwesenheit.anlegen", entity_type="abwesenheit", entity_id=ab.id,
        detail=f"{person.name} {payload.von}–{payload.bis} ({payload.art})",
    )
    db.commit()
    db.refresh(ab)
    out = AbwesenheitOut.model_validate(ab)
    out.person_name = ab.person.name if ab.person else None
    return out


@router.put("/{absence_id}", response_model=AbwesenheitOut, status_code=status.HTTP_200_OK)
def update_absence(
    absence_id: int,
    payload: AbwesenheitCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    ab = db.get(Abwesenheit, absence_id)
    if ab is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abwesenheit nicht gefunden")
    person = db.get(Person, payload.person_id)
    if person is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Person fehlt")
    if payload.bis < payload.von:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "bis vor von")

    ab.person_id = payload.person_id
    ab.von = payload.von
    ab.bis = payload.bis
    ab.art = payload.art
    ab.bemerkung = payload.bemerkung
    write_audit(
        db, user, action="abwesenheit.aendern", entity_type="abwesenheit", entity_id=ab.id,
        detail=f"{person.name} {payload.von}–{payload.bis}",
    )
    db.commit()
    db.refresh(ab)
    out = AbwesenheitOut.model_validate(ab)
    out.person_name = ab.person.name if ab.person else None
    return out


@router.delete("/{absence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_absence(
    absence_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_staff),
):
    ab = db.get(Abwesenheit, absence_id)
    if ab is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Abwesenheit nicht gefunden")
    name = ab.person.name if ab.person else str(ab.person_id)
    write_audit(
        db, user, action="abwesenheit.loeschen", entity_type="abwesenheit", entity_id=ab.id,
        detail=f"{name} {ab.von}–{ab.bis}",
    )
    db.delete(ab)
    db.commit()
