"""Person Portal - Login und Selbstverwaltung."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import create_access_token, verify_password, hash_password, decode_token
from app.db.base import get_db
from app.models.models import Person, Verfuegbarkeit, Abwesenheit, Mitgliedschaft
from app.schemas.schemas import PersonOut, VerfuegbarkeitBulk, AbwesenheitCreate, AbwesenheitOut

router = APIRouter(prefix="/person", tags=["Person Portal"])


def get_current_person(authorization: str = Header(None), db: Session = Depends(get_db)) -> Person:
    """Validiere JWT Token und gib aktuelle Person zurück."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing or invalid token")

    token = authorization.split(" ", 1)[1]
    payload = decode_token(token)
    if not payload or "person_id" not in payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    person_id = payload["person_id"]
    person = db.get(Person, person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found")
    return person

@router.post("/login")
async def login(email: str = None, password: str = None, db: Session = Depends(get_db)):
    """Login mit Email + Passwort → JWT Token (Query-Params oder Body)."""
    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing email or password")

    person = db.query(Person).filter(Person.email == email).first()
    if not person or not person.password_hash or not verify_password(password, person.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not person.aktiv:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Person is inactive")

    token = create_access_token({"person_id": person.id, "email": person.email})
    return {"access_token": token, "token_type": "bearer", "person_id": person.id, "name": f"{person.vorname} {person.nachname}"}


@router.get("/me", response_model=PersonOut)
def get_me(person: Person = Depends(get_current_person)):
    """Hole Profildaten der aktuellen Person."""
    return person


class ProfileUpdateRequest(BaseModel):
    vorname: str | None = None
    nachname: str | None = None
    partei: str | None = None
    gremium: str | None = None


@router.put("/me")
def update_me(
    request: ProfileUpdateRequest | None = None,
    vorname: str | None = None,
    nachname: str | None = None,
    partei: str | None = None,
    gremium: str | None = None,
    person: Person = Depends(get_current_person),
    db: Session = Depends(get_db),
):
    """Update Profildaten (außer Email und Passwort). Accepts JSON body or query params."""
    # Handle JSON body
    if request:
        if request.vorname:
            person.vorname = request.vorname
        if request.nachname:
            person.nachname = request.nachname
        if request.partei is not None:
            person.partei = request.partei
        if request.gremium is not None:
            person.gremium = request.gremium

    # Handle query parameters (override body)
    if vorname:
        person.vorname = vorname
    if nachname:
        person.nachname = nachname
    if partei is not None:
        person.partei = partei
    if gremium is not None:
        person.gremium = gremium

    db.commit()
    db.refresh(person)
    return person


@router.put("/me/password")
def change_password(
    old_password: str = None,
    new_password: str = None,
    person: Person = Depends(get_current_person),
    db: Session = Depends(get_db),
):
    """Ändere das Passwort (Query-Params oder Body)."""
    if not old_password or not new_password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing old_password or new_password")

    if not person.password_hash or not verify_password(old_password, person.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid current password")

    person.password_hash = hash_password(new_password)
    db.commit()
    return {"message": "Password changed successfully"}


@router.put("/me/verfuegbarkeiten")
def set_verfuegbarkeiten(
    bulk: VerfuegbarkeitBulk,
    person: Person = Depends(get_current_person),
    db: Session = Depends(get_db),
):
    """Setze die Standardverfügbarkeit (periode_id=NULL). Perioden-Overrides bleiben erhalten."""
    db.query(Verfuegbarkeit).filter(
        Verfuegbarkeit.person_id == person.id,
        Verfuegbarkeit.periode_id.is_(None),
    ).delete()

    for item in bulk.items:
        if not item.verfuegbar:
            continue  # nur positive Einträge speichern (wie Admin-API)
        db.add(Verfuegbarkeit(
            person_id=person.id,
            periode_id=None,
            wochentag=item.wochentag,
            stunde=item.stunde,
            verfuegbar=True,
        ))

    db.commit()
    return db.query(Verfuegbarkeit).filter(
        Verfuegbarkeit.person_id == person.id,
        Verfuegbarkeit.periode_id.is_(None),
    ).all()


@router.get("/me/verfuegbarkeiten")
def get_verfuegbarkeiten(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    """Hole die Standardverfügbarkeit der aktuellen Person."""
    return db.query(Verfuegbarkeit).filter(
        Verfuegbarkeit.person_id == person.id,
        Verfuegbarkeit.periode_id.is_(None),
    ).all()


@router.post("/me/absences", response_model=AbwesenheitOut)
def create_absence(
    req: AbwesenheitCreate,
    person: Person = Depends(get_current_person),
    db: Session = Depends(get_db),
):
    """Trage eine Abwesenheit für dich selbst ein."""
    if req.bis < req.von:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Enddatum muss nach dem Startdatum liegen",
        )
    absence = Abwesenheit(
        person_id=person.id,
        von=req.von,
        bis=req.bis,
        art=req.art,
        bemerkung=req.bemerkung,
    )
    db.add(absence)
    db.commit()
    db.refresh(absence)
    return {**absence.__dict__, "person_name": person.name}


@router.get("/me/absences")
def get_my_absences(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    """Hole meine Abwesenheiten."""
    absences = db.query(Abwesenheit).filter(Abwesenheit.person_id == person.id).all()
    return [
        {**a.__dict__, "person_name": person.name}
        for a in absences
    ]


@router.get("/me/committees")
def get_my_committees(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    """Hole meine Ausschuss-Mitgliedschaften."""
    memberships = db.query(Mitgliedschaft).filter(Mitgliedschaft.person_id == person.id).all()
    result = []
    for m in memberships:
        result.append({
            "ausschuss_id": m.ausschuss_id,
            "ausschuss_name": m.ausschuss.name,
            "typ": m.ausschuss.typ,
            "rolle": m.rolle,
        })
    return result


@router.get("/me/sitzungen")
def get_my_sitzungen(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    """Fixierte Sitzungstermine der eigenen Ausschüsse."""
    from app.models.models import Sitzungsvorschlag
    from app.schemas.schemas import SitzungsvorschlagOut

    ausschuss_ids = [
        m.ausschuss_id
        for m in db.query(Mitgliedschaft).filter(Mitgliedschaft.person_id == person.id).all()
    ]
    if not ausschuss_ids:
        return []
    rows = (
        db.query(Sitzungsvorschlag)
        .filter(
            Sitzungsvorschlag.ausschuss_id.in_(ausschuss_ids),
            Sitzungsvorschlag.abgesagt.is_(False),
        )
        .all()
    )
    return [SitzungsvorschlagOut.model_validate(r) for r in rows]


@router.get("/me/sitzungen.pdf")
def export_my_sitzungen_pdf(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    """PDF der eigenen fixierten Sitzungen (für späteres Person-Portal)."""
    from datetime import date as date_cls

    from fastapi.responses import Response

    from app.models.models import Sitzungsvorschlag
    from app.services.pdf_service import (
        build_wochenplan_pdf,
        load_ausschuss_namen,
        vorschlaege_to_plan,
    )

    ausschuss_ids = [
        m.ausschuss_id
        for m in db.query(Mitgliedschaft).filter(Mitgliedschaft.person_id == person.id).all()
    ]
    rows = []
    if ausschuss_ids:
        rows = (
            db.query(Sitzungsvorschlag)
            .filter(
                Sitzungsvorschlag.ausschuss_id.in_(ausschuss_ids),
                Sitzungsvorschlag.abgesagt.is_(False),
            )
            .order_by(Sitzungsvorschlag.woche, Sitzungsvorschlag.wochentag, Sitzungsvorschlag.start_minute)
            .all()
        )
    namen = load_ausschuss_namen(db, {r.ausschuss_id for r in rows})
    anchors = {r.planungs_start_datum for r in rows if r.planungs_start_datum}
    start = next(iter(anchors)) if len(anchors) == 1 else None
    pdf = build_wochenplan_pdf(
        vorschlaege_to_plan(rows, namen),
        titel=f"Meine Sitzungen – {person.vorname} {person.nachname}",
        untertitel=f"Planungsstart: {start.strftime('%d.%m.%Y')}" if start else None,
        start_datum=start,
    )
    filename = f"meine_sitzungen_{date_cls.today().isoformat()}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/me/dashboard")
def get_dashboard(person: Person = Depends(get_current_person), db: Session = Depends(get_db)):
    """Dashboard Stats für die aktuelle Person."""
    from app.models.enums import Wochentag

    # Verfügbare Stunden diese Woche
    today_wochentag = None  # Würde in Prod mit datetime.today().weekday() berechnet
    verfugbar_hours = db.query(Verfuegbarkeit).filter(
        Verfuegbarkeit.person_id == person.id,
        Verfuegbarkeit.verfuegbar.is_(True)
    ).count()

    # Ausschüsse
    committee_count = db.query(Mitgliedschaft).filter(
        Mitgliedschaft.person_id == person.id
    ).count()

    # Aktive Abwesenheiten (diese Woche/Monat)
    absence_count = db.query(Abwesenheit).filter(
        Abwesenheit.person_id == person.id
    ).count()

    return {
        "name": person.name,
        "email": person.email,
        "verfugbar_stunden": verfugbar_hours,
        "ausschuesse": committee_count,
        "abwesenheiten": absence_count,
    }


@router.post("/set-password")
def set_password(token: str, new_password: str, db: Session = Depends(get_db)):
    """Setze Passwort mit Einladungs-Token."""
    from datetime import datetime, timezone

    person = db.query(Person).filter(Person.invite_token == token).first()
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid token")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    if not person.invite_expires or now > person.invite_expires:
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="Token expired")

    person.password_hash = hash_password(new_password)
    person.invite_token = None
    person.invite_expires = None
    db.commit()
    return {"message": "Password set successfully. You can now login."}
