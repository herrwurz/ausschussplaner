"""Export-Endpunkte: PDF-Formulare und weitere Downloads."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.api.deps import require_staff
from app.db.base import get_db
from app.models.models import Person, Sitzungsvorschlag
from app.services.ics_service import build_sitzungen_ics
from app.services.pdf_forms import FormPerson, build_gr_erhebungsbogen_pdf
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


@router.get("/formular/erhebung.pdf")
def export_erhebungsbogen(
    periode: str | None = Query(None, description="Optionaler Perioden-Text auf dem Formular"),
    db: Session = Depends(get_db),
):
    """Ein GR-Erhebungsbogen: Name | Abwesenheit | Verfügbarkeits-Uhrzeiten."""
    personen = _active_form_persons(db)
    pdf = build_gr_erhebungsbogen_pdf(personen, periode_label=periode or "")
    filename = f"erhebungsbogen_{date.today().isoformat()}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Aliase für bestehende Frontend-Links
@router.get("/formular/verfuegbarkeit.pdf")
@router.get("/formular/abwesenheit.pdf")
def export_erhebungsbogen_alias(
    periode: str | None = Query(None),
    mit_namen: bool = Query(True),  # ignoriert — immer alle aktiven Personen
    db: Session = Depends(get_db),
):
    return export_erhebungsbogen(periode=periode, db=db)


@router.get("/sitzungen.ics")
def export_sitzungen_ics(db: Session = Depends(get_db)):
    """ICS-Kalender aller fixierten Sitzungstermine (für Outlook/Google Kalender)."""
    rows = (
        db.query(Sitzungsvorschlag)
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
