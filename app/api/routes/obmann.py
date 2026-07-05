"""Obmann-Dashboard Routes - Ausschuss-Management für Obmänner."""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.base import get_db
from app.models.models import User, Ausschuss, Mitgliedschaft, Sitzungsvorschlag
from app.models.enums import Rolle
from app.services.calculation_service import run_calculation
from app.schemas.schemas import BerechnungRequest
from app.services.auth_service import TokenService

router = APIRouter(prefix="/obmann", tags=["Obmann"])


def get_current_obmann(
    db: Session = Depends(get_db),
    authorization: str = Header(None),
) -> User:
    """Hole aktuellen Obmann aus Authorization Header."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Nicht authentifiziert",
        )

    token = authorization.split(" ")[1]
    payload = TokenService.decode_token(token)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ungültiger Token",
        )

    user_id = int(payload["sub"])
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Benutzer nicht gefunden",
        )

    return user


@router.get("/ausschuesse")
def get_obmann_ausschuesse(
    obmann: User = Depends(get_current_obmann),
    db: Session = Depends(get_db),
):
    """Hole alle Ausschüsse, bei denen der aktuelle Benutzer Obmann ist."""

    # Für jetzt: Gebe alle aktiven Ausschüsse zurück
    # TODO: Implementiere richtige Obmann-Überprüfung über Person ↔ Ausschuss-Mitgliedschaften
    ausschuesse = db.query(Ausschuss).filter(Ausschuss.aktiv == True).all()

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

    # Hole alle Ausschüsse des Obmans
    ausschuesse = db.query(Ausschuss).filter(Ausschuss.aktiv == True).all()
    ausschuss_ids = [a.id for a in ausschuesse]

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

    # TODO: Überprüfe, ob der aktuelle Benutzer Obmann dieses Ausschusses ist

    try:
        # Erstelle BerechnungRequest für den Ausschuss
        req = BerechnungRequest(
            ausschuss_id=ausschuss_id,
            start_date=None,
            weeks=2,
        )

        result = run_calculation(db, req)

        return {
            "success": True,
            "ausschuss_id": ausschuss_id,
            "ausschuss_name": ausschuss.name,
            "results": {
                "slot_count": len(result.slots) if hasattr(result, 'slots') else 0,
                "data": result,
            },
        }
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Berechnung fehlgeschlagen: {str(e)}",
        )
