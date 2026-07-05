"""API-Routen für Personenverwaltung."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.models import Person, Verfuegbarkeit
from app.schemas.schemas import (
    AgendaTransfer,
    AgendaTransferResult,
    PersonCreate,
    PersonOut,
    PersonUpdate,
    VerfuegbarkeitBulk,
    VerfuegbarkeitOut,
)
from app.services.person_service import transfer_agenda

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


# ── Aktivieren / Deaktivieren ──
@router.post("/{person_id}/deactivate", response_model=PersonOut)
def deactivate_person(person_id: int, db: Session = Depends(get_db)):
    """Setzt eine Person inaktiv (z. B. ausgeschieden)."""
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    person.aktiv = False
    db.commit()
    db.refresh(person)
    return person


@router.post("/{person_id}/activate", response_model=PersonOut)
def activate_person(person_id: int, db: Session = Depends(get_db)):
    """Reaktiviert eine Person."""
    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    person.aktiv = True
    db.commit()
    db.refresh(person)
    return person


# ── Agenden-Übernahme / Nachfolge ──
@router.post("/transfer-agenda", response_model=AgendaTransferResult)
def post_transfer_agenda(payload: AgendaTransfer, db: Session = Depends(get_db)):
    """Überträgt alle Ausschuss-Agenden von einer Person auf eine andere.

    Anwendungsfall: ausgeschiedenes Mandat wird durch eine neue Person ersetzt;
    die neue Person übernimmt sämtliche Rollen/Mitgliedschaften.
    """
    try:
        return transfer_agenda(db, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


# ── Verfügbarkeiten ──
@router.get("/{person_id}/verfuegbarkeit", response_model=list[VerfuegbarkeitOut])
def get_verfuegbarkeit(
    person_id: int,
    periode_id: int | None = None,
    effektiv: bool = False,
    db: Session = Depends(get_db),
):
    """Verfügbarkeit einer Person.

    - periode_id=None: Standardverfügbarkeit (Einträge ohne Periode)
    - periode_id=X: nur die Einträge dieser Periode
    - effektiv=True (mit periode_id): Perioden-Einträge, falls vorhanden,
      sonst Fallback auf die Standardverfügbarkeit (wie in der Berechnung)
    """
    if db.get(Person, person_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    scope = db.scalars(
        select(Verfuegbarkeit).where(
            Verfuegbarkeit.person_id == person_id,
            Verfuegbarkeit.periode_id == periode_id,
        )
    ).all()
    if effektiv and periode_id is not None and not scope:
        scope = db.scalars(
            select(Verfuegbarkeit).where(
                Verfuegbarkeit.person_id == person_id,
                Verfuegbarkeit.periode_id.is_(None),
            )
        ).all()
    return scope


@router.put("/{person_id}/verfuegbarkeit", response_model=list[VerfuegbarkeitOut])
def set_verfuegbarkeit(
    person_id: int,
    payload: VerfuegbarkeitBulk,
    periode_id: int | None = None,
    db: Session = Depends(get_db),
):
    """Ersetzt die Verfügbarkeit einer Person für den gewählten Geltungsbereich.

    periode_id=None ersetzt die Standardverfügbarkeit, periode_id=X nur die
    Einträge dieser Periode (Standardeinträge bleiben unberührt).
    """
    if db.get(Person, person_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")
    db.query(Verfuegbarkeit).filter(
        Verfuegbarkeit.person_id == person_id,
        Verfuegbarkeit.periode_id == periode_id,
    ).delete()
    for item in payload.items:
        db.add(Verfuegbarkeit(person_id=person_id, periode_id=periode_id, **item.model_dump()))
    db.commit()
    return db.scalars(
        select(Verfuegbarkeit).where(
            Verfuegbarkeit.person_id == person_id,
            Verfuegbarkeit.periode_id == periode_id,
        )
    ).all()


# ── Einladungs-Email ──
@router.post("/{person_id}/send-invitation")
def send_invitation(person_id: int, db: Session = Depends(get_db)):
    """Generiert Einladungs-Token und sendet Email."""
    import asyncio
    from app.services.email_service import generate_invite_token, send_invitation_email

    person = db.get(Person, person_id)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Person nicht gefunden")

    if not person.email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Person hat keine Email-Adresse")

    token, expires = generate_invite_token()
    person.invite_token = token
    person.invite_expires = expires
    db.commit()

    try:
        asyncio.run(send_invitation_email(person.email, token, f"{person.vorname} {person.nachname}"))
        return {"message": f"Einladungs-Email an {person.email} gesendet"}
    except Exception as e:
        return {"message": f"Email versand fehlgeschlagen: {str(e)}", "token": token}
