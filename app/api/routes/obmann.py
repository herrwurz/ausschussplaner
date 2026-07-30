"""Obmann-Dashboard Routes - Ausschuss-Management für Obmänner."""
import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.base import get_db
from app.models.enums import BenutzerRolle, Rolle
from app.models.models import Ausschuss, Mitgliedschaft, Person, User
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

    SUPER_ADMIN: alle aktiven Ausschüsse.
    Obmann: explizite `obmann_ausschuss_ids` plus Ausschüsse, in denen die
    Person mit gleicher E-Mail als Obmann / Obmann-Stv. eingetragen ist.
    """
    if obmann.rolle == BenutzerRolle.SUPER_ADMIN:
        rows = db.query(Ausschuss.id).filter(Ausschuss.aktiv == True).all()  # noqa: E712
        return {r[0] for r in rows}

    ids: set[int] = set()
    try:
        ids |= {int(i) for i in json.loads(obmann.obmann_ausschuss_ids or "[]")}
    except (TypeError, ValueError, json.JSONDecodeError):
        pass

    person = (
        db.query(Person)
        .filter(Person.email == obmann.email, Person.aktiv == True)  # noqa: E712
        .first()
    )
    if person:
        rows = (
            db.query(Mitgliedschaft.ausschuss_id)
            .filter(
                Mitgliedschaft.person_id == person.id,
                Mitgliedschaft.rolle.in_([Rolle.OBMANN, Rolle.OBMANN_STELLVERTRETER]),
            )
            .all()
        )
        ids |= {r[0] for r in rows}

    return ids


@router.get("/ausschuesse")
def get_obmann_ausschuesse(
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Hole alle Ausschüsse, bei denen der aktuelle Benutzer Obmann ist."""
    ids = erlaubte_ausschuss_ids(obmann, db)
    if not ids:
        return []

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
    if not ausschuss_ids:
        return []

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
    periode_id: int | None = None,
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Effektive Verfügbarkeit einer Person (Standard bzw. Perioden-Override)."""
    from app.models.enums import Wochentag
    from app.models.models import Person, Verfuegbarkeit

    person = db.query(Person).filter(Person.id == person_id).first()
    if not person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Person nicht gefunden",
        )

    ids = erlaubte_ausschuss_ids(obmann, db)
    if not ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Keine Ausschüsse zugewiesen",
        )

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

    scope = []
    if periode_id is not None:
        scope = (
            db.query(Verfuegbarkeit)
            .filter(
                Verfuegbarkeit.person_id == person_id,
                Verfuegbarkeit.periode_id == periode_id,
            )
            .all()
        )
    if not scope:
        scope = (
            db.query(Verfuegbarkeit)
            .filter(
                Verfuegbarkeit.person_id == person_id,
                Verfuegbarkeit.periode_id.is_(None),
            )
            .all()
        )

    by_day: dict[str, list[dict]] = {d.value: [] for d in Wochentag}
    for v in scope:
        if not v.verfuegbar:
            continue
        day = v.wochentag.value if v.wochentag else None
        if day not in by_day:
            continue
        by_day[day].append({"stunde": v.stunde, "verfuegbar": True})
    for day in by_day:
        by_day[day].sort(key=lambda s: s["stunde"])

    return {
        "person_id": person_id,
        "name": f"{person.vorname} {person.nachname}",
        "verfuegbarkeiten": by_day,
        "slots": [
            {"wochentag": day, "stunde": s["stunde"], "verfuegbar": True}
            for day, slots in by_day.items()
            for s in slots
        ],
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

        def _slot(v) -> dict:
            return {
                "woche": v.woche,
                "wochentag": v.wochentag.value if hasattr(v.wochentag, "value") else str(v.wochentag),
                "start": v.start,
                "ende": v.ende,
                "datum": v.datum.isoformat() if v.datum else None,
                "quote": v.quote,
                "status": v.status.value if hasattr(v.status, "value") else str(v.status),
                "empfehlung": v.empfehlung,
                "anwesend": v.anwesend,
                "mitglieder": v.mitglieder,
                "obmann_da": v.obmann_da,
                "stv_da": v.stv_da,
                "fehlende": v.fehlende or [],
            }

        vorschlaege = []
        if analyse:
            # Beste je Tag, sonst Top, sonst Beschlussfähig
            quelle = analyse.beste_je_tag or analyse.top_termine or analyse.beschlussfaehig
            vorschlaege = [_slot(v) for v in quelle[:12]]

        return {
            "success": True,
            "ausschuss_id": ausschuss_id,
            "ausschuss_name": ausschuss.name,
            "empfehlung_text": analyse.empfehlung_text if analyse else "",
            "slot_count": len(vorschlaege),
            "vorschlaege": vorschlaege,
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Berechnung fehlgeschlagen: {str(e)}",
        ) from e
