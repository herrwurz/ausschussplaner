"""Obmann-Dashboard Routes - Ausschuss-Management für Obmänner."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.enums import BenutzerRolle
from app.models.models import Ausschuss, Mitgliedschaft, User
from app.schemas.schemas import BerechnungRequest
from app.services.calculation_service import run_calculation

router = APIRouter(prefix="/obmann", tags=["Obmann"])


def get_current_obmann(user: User = Depends(get_current_user)) -> User:
    """Erlaube nur Obmänner und Super-Admins (403 sonst)."""
    if user.rolle not in (BenutzerRolle.OBMANN, BenutzerRolle.SUPER_ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Zugriff auf das Obmann-Dashboard",
        )
    return user


def erlaubte_ausschuss_ids(obmann: User, db: Session) -> set[int]:
    """IDs der Ausschüsse, die der Benutzer verwalten darf.

    SUPER_ADMIN darf alle aktiven Ausschüsse, ein Obmann nur die ihm in
    `User.obmann_ausschuss_ids` (JSON-Liste) zugewiesenen.
    """
    if obmann.rolle == BenutzerRolle.SUPER_ADMIN:
        rows = db.query(Ausschuss.id).filter(Ausschuss.aktiv == True).all()  # noqa: E712
        return {r[0] for r in rows}
    try:
        ids = json.loads(obmann.obmann_ausschuss_ids or "[]")
        return {int(i) for i in ids}
    except (TypeError, ValueError):
        return set()


@router.get("/ausschuesse")
def get_obmann_ausschuesse(
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Hole alle Ausschüsse, bei denen der aktuelle Benutzer Obmann ist."""
    ids = erlaubte_ausschuss_ids(obmann, db)
    ausschuesse = (
        db.query(Ausschuss)
        .filter(Ausschuss.aktiv == True, Ausschuss.id.in_(ids))  # noqa: E712
        .all()
    )

    return [
        {
            "id": a.id,
            "name": a.name,
            "typ": a.typ.value if a.typ else "standard",
            "aktiv": a.aktiv,
        }
        for a in ausschuesse
    ]


@router.get("/personen")
def get_obmann_personen(
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Hole alle Personen aus den Ausschüssen des Obmans."""
    from app.models.models import Person

    ausschuss_ids = erlaubte_ausschuss_ids(obmann, db)

    # Hole alle Personen, die in diesen Ausschüssen Mitglied sind
    personen = (
        db.query(Person)
        .join(Mitgliedschaft, Person.id == Mitgliedschaft.person_id)
        .filter(Mitgliedschaft.ausschuss_id.in_(ausschuss_ids))
        .distinct()
        .all()
    )

    return [
        {
            "id": p.id,
            "vorname": p.vorname,
            "nachname": p.nachname,
            "email": p.email,
            "gremium": p.gremium,
            "aktiv": p.aktiv,
        }
        for p in personen
    ]


@router.get("/personen/{person_id}/verfuegbarkeit")
def get_obmann_person_verfuegbarkeit(
    person_id: int,
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Hole Verfügbarkeit einer Person des Obmans."""
    from app.models.models import Person, Verfuegbarkeit

    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person nicht gefunden",
        )

    # Nur Personen aus den eigenen Ausschüssen des Obmans
    ids = erlaubte_ausschuss_ids(obmann, db)
    ist_mitglied = (
        db.query(Mitgliedschaft)
        .filter(
            Mitgliedschaft.person_id == person_id,
            Mitgliedschaft.ausschuss_id.in_(ids),
        )
        .first()
    )
    if not ist_mitglied:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Person gehört zu keinem Ausschuss dieses Obmans",
        )

    verfuegbarkeiten = (
        db.query(Verfuegbarkeit)
        .filter(Verfuegbarkeit.person_id == person_id)
        .all()
    )

    # Gruppiere nach Wochentag
    by_day = {}
    for v in verfuegbarkeiten:
        day = v.wochentag.value if v.wochentag else "unknown"
        if day not in by_day:
            by_day[day] = []
        by_day[day].append({
            "stunde": v.stunde,
            "verfuegbar": v.verfuegbar,
        })

    return {
        "person_id": person_id,
        "name": f"{person.vorname} {person.nachname}",
        "verfuegbarkeiten": by_day,
    }


@router.post("/calculate/{ausschuss_id}")
def calculate_ausschuss_termine(
    ausschuss_id: int,
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Berechne Sitzungstermine für einen Ausschuss."""

    ausschuss = db.query(Ausschuss).filter(Ausschuss.id == ausschuss_id).first()
    if not ausschuss:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ausschuss nicht gefunden",
        )

    if ausschuss_id not in erlaubte_ausschuss_ids(obmann, db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Kein Obmann dieses Ausschusses",
        )

    try:
        req = BerechnungRequest(
            ausschuss_ids=[ausschuss_id],
            planungswochen=2,
            periode_id=ausschuss.periode_id,
        )

        result = run_calculation(db, req)
        analyse = next(
            (a for a in result.analysen if a.ausschuss_id == ausschuss_id),
            None,
        )
        slot_count = len(analyse.beste_je_tag) if analyse else 0

        return {
            "success": True,
            "ausschuss_id": ausschuss_id,
            "ausschuss_name": ausschuss.name,
            "results": {
                "slot_count": slot_count,
                "data": result,
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Berechnung fehlgeschlagen: {str(e)}",
        ) from e
