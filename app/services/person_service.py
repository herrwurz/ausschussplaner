"""Geschäftslogik rund um Personen: Agenden-Übernahme / Nachfolge."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import Mitgliedschaft, Person, Verfuegbarkeit
from app.schemas.schemas import AgendaTransfer, AgendaTransferResult


def transfer_agenda(db: Session, payload: AgendaTransfer) -> AgendaTransferResult:
    """Überträgt alle Mitgliedschaften (Rollen) von einer Person auf eine andere.

    Ablauf:
      1. Alle Mitgliedschaften der Quellperson laden.
      2. Für jede: existiert bei der Zielperson bereits eine Mitgliedschaft
         im selben Ausschuss? -> überspringen. Sonst -> umhängen.
      3. Optional: Verfügbarkeit der Quelle auf das Ziel kopieren.
      4. Optional: Quellperson deaktivieren.
    """
    von = db.get(Person, payload.von_person_id)
    zu = db.get(Person, payload.zu_person_id)
    if von is None or zu is None:
        raise ValueError("Quell- oder Zielperson nicht gefunden")
    if von.id == zu.id:
        raise ValueError("Quell- und Zielperson sind identisch")

    quell_ms = db.scalars(
        select(Mitgliedschaft).where(Mitgliedschaft.person_id == von.id)
    ).all()

    ziel_ausschuesse = {
        ms.ausschuss_id
        for ms in db.scalars(
            select(Mitgliedschaft).where(Mitgliedschaft.person_id == zu.id)
        ).all()
    }

    uebertragen = 0
    uebersprungen = 0
    for ms in quell_ms:
        if ms.ausschuss_id in ziel_ausschuesse:
            uebersprungen += 1
            continue
        ms.person_id = zu.id  # Mitgliedschaft umhängen (Rolle bleibt erhalten)
        uebertragen += 1

    verf_kopiert = False
    if payload.verfuegbarkeit_uebernehmen:
        # Perioden-bewusst: Ziel-Einträge je Scope ersetzen, periode_id mitkopieren
        db.query(Verfuegbarkeit).filter(Verfuegbarkeit.person_id == zu.id).delete()
        quell_verf = db.scalars(
            select(Verfuegbarkeit).where(Verfuegbarkeit.person_id == von.id)
        ).all()
        for v in quell_verf:
            db.add(Verfuegbarkeit(
                person_id=zu.id,
                periode_id=v.periode_id,
                wochentag=v.wochentag,
                stunde=v.stunde,
                verfuegbar=v.verfuegbar,
            ))
        verf_kopiert = True

    if payload.quelle_deaktivieren:
        von.aktiv = False

    db.commit()
    return AgendaTransferResult(
        von_person_id=von.id,
        zu_person_id=zu.id,
        uebertragene_mitgliedschaften=uebertragen,
        uebersprungen=uebersprungen,
        quelle_deaktiviert=payload.quelle_deaktivieren,
        verfuegbarkeit_kopiert=verf_kopiert,
    )
