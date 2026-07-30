"""Export-Endpunkte: PDF-Formulare und weitere Downloads."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.base import get_db
from app.models.models import Person, Sitzungsvorschlag
from app.services.ics_service import build_sitzungen_ics
from app.services.pdf_forms import (
    FormPerson,
    build_abwesenheit_formular_pdf,
    build_verfuegbarkeit_formular_pdf,
)
from app.services.pdf_service import load_ausschuss_namen

router = APIRouter(
    prefix="/export",
    tags=["Export"],
    dependencies=[Depends(require_staff)],
)


def _active_form_persons(db: Session) -> list[FormPerson]:
    rows = (
        db.query(Person)
        .filter(Person.aktiv.is_(True))
        .order_by(Person.nachname, Person.vorname)
        .all()
    )
    return [
        FormPerson(
            name=f"{p.vorname} {p.nachname}".strip(),
            gremium=p.gremium or "",
        )
        for p in rows
    ]


@router.get("/formular/verfuegbarkeit.pdf")
def export_verfuegbarkeit_formular(
    periode: str | None = Query(None, description="Optionaler Perioden-Text"),
    db: Session = Depends(get_db),
):
    """PDF Verfügbarkeit: Name | Uhrzeiten (alle aktiven Personen)."""
    pdf = build_verfuegbarkeit_formular_pdf(
        _active_form_persons(db),
        periode_label=periode or "",
    )
    filename = f"formular_verfuegbarkeit_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/formular/abwesenheit.pdf")
def export_abwesenheit_formular(db: Session = Depends(get_db)):
    """PDF Abwesenheit: Name | leere Zeile (alle aktiven Personen)."""
    pdf = build_abwesenheit_formular_pdf(_active_form_persons(db))
    filename = f"formular_abwesenheit_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/sitzungen.ics")
def export_sitzungen_ics(db: Session = Depends(get_db)):
    """ICS-Kalender aller fixierten Sitzungstermine."""
    rows = (
        db.query(Sitzungsvorschlag)
        .filter(Sitzungsvorschlag.abgesagt.is_(False))
        .order_by(Sitzungsvorschlag.woche, Sitzungsvorschlag.wochentag, Sitzungsvorschlag.start_minute)
        .all()
    )
    namen = load_ausschuss_namen(db, {r.ausschuss_id for r in rows})
    ics = build_sitzungen_ics(rows, ausschuss_namen=namen)
    filename = f"sitzungen_{date.today().isoformat()}.ics"
    return Response(
        content=ics.encode("utf-8"),
        media_type="text/calendar; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/sync-verfuegbarkeiten")
def sync_verfuegbarkeiten_endpoint():
    """Standardverfügbarkeiten sofort an realdata.json angleichen (Admin)."""
    from sync_verfuegbarkeiten import sync_verfuegbarkeiten

    try:
        diffs = sync_verfuegbarkeiten(fix=True)
    except FileNotFoundError as err:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(err)) from err
    except Exception as err:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, str(err)) from err
    return {
        "ok": True,
        "personen_korrigiert_oder_geprueft": diffs,
        "message": "Standardverfügbarkeiten an realdata.json angeglichen "
        "(perioden-spezifische Einträge entfernt).",
    }
