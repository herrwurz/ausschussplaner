"""API-Routen für Personenverwaltung."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import Person, Verfuegbarkeit
from app.schemas.schemas import (
    PersonCreate,
    PersonOut,
    PersonUpdate,
    VerfuegbarkeitBulk,
    VerfuegbarkeitOut,
)

router = APIRouter(prefix="/persons", tags=["Personen"])


@router.get("", response_model=list[PersonOut])
def list_persons(aktiv_only: bool = False, db: Session = Depends(get_db)):
    stmt = select(Person)
    if aktiv_only:
        stmt = stmt.where(Person.aktiv.is_(True))
    return db.scalars(stmt.order_by(Person.nachname)).all()


@router.post("", response_model=PersonOut, status_code=status.HTTP_201_CREATED)
def create_person(payload: PersonCreate, db: Session = Depends(get_db)):
    person = Person(**payload.model_dump())
    db.add(person)
    db.commit()
    db.refresh(person)
    return person


@router.get("/{person_id}", response_model=PersonOut)
def get_person(person_id: int, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    return person


@router.patch("/{person_id}", response_model=PersonOut)
def update_person(person_id: int, payload: PersonUpdate, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(person, k, v)
    db.commit()
    db.refresh(person)
    return person


@router.delete("/{person_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_person(person_id: int, db: Session = Depends(get_db)):
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    db.delete(person)
    db.commit()


# ── Verfügbarkeiten ──
@router.get("/{person_id}/verfuegbarkeit", response_model=list[VerfuegbarkeitOut])
def get_verfuegbarkeit(person_id: int, db: Session = Depends(get_db)):
    if db.get(Person, person_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    return db.scalars(
        select(Verfuegbarkeit).where(Verfuegbarkeit.person_id == person_id)
    ).all()


@router.put("/{person_id}/verfuegbarkeit", response_model=list[VerfuegbarkeitOut])
def set_verfuegbarkeit(
    person_id: int, payload: VerfuegbarkeitBulk, db: Session = Depends(get_db)
):
    """Ersetzt die gesamte Verfügbarkeit einer Person."""
    if db.get(Person, person_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    db.query(Verfuegbarkeit).filter(Verfuegbarkeit.person_id == person_id).delete()
    for item in payload.items:
        db.add(Verfuegbarkeit(person_id=person_id, **item.model_dump()))
    db.commit()
    return db.scalars(
        select(Verfuegbarkeit).where(Verfuegbarkeit.person_id == person_id)
    ).all()
