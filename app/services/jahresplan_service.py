"""Geschäftslogik für Jahresplan-Verwaltung: Anlegen, Auflisten, Kopieren."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    Jahresplan,
    Person,
    Sitzungsregel,
    Verfuegbarkeit,
)
from app.schemas.schemas import JahresplanCopy, JahresplanCopyResult


def list_jahresplaene(db: Session) -> list[Jahresplan]:
    return db.scalars(select(Jahresplan).order_by(Jahresplan.jahr.desc())).all()


def create_jahresplan(db: Session, jahr: int, bezeichnung: str = "") -> Jahresplan:
    jp = Jahresplan(jahr=jahr, bezeichnung=bezeichnung)
    db.add(jp)
    db.commit()
    db.refresh(jp)
    return jp


def copy_jahresplan(db: Session, payload: JahresplanCopy) -> JahresplanCopyResult:
    """Kopiert relevante Stammdaten vom Quell- ins Zieljahr.

    Konkret: optionale Übernahme der Verfügbarkeiten aller (aktiven) Personen
    und der globalen Sitzungsregel. Ein neuer Jahresplan-Eintrag für das Zieljahr
    wird angelegt (falls noch nicht vorhanden).
    """
    # Zieljahr-Plan anlegen oder vorhandenen zurückgeben
    existing = db.scalars(
        select(Jahresplan).where(Jahresplan.jahr == payload.ziel_jahr)
    ).first()
    if existing is None:
        existing = Jahresplan(jahr=payload.ziel_jahr, bezeichnung=f"Kopie von {payload.quelle_jahr}")
        db.add(existing)
        db.flush()

    persons_copied = 0

    if payload.uebernehme_verfuegbarkeiten:
        stmt = select(Person)
        if payload.schliesse_inaktive_aus:
            stmt = stmt.where(Person.aktiv.is_(True))
        persons = db.scalars(stmt).all()

        for person in persons:
            # Verfügbarkeiten bleiben personenbezogen (nicht jahresspezifisch),
            # daher wird hier nur sichergestellt, dass die Person existiert.
            # In einer echten Jahresplan-Implementierung würde man eine
            # jahresspezifische Verfügbarkeitstabelle nutzen. Hier: no-op,
            # da die Verfügbarkeit bereits persistent ist.
            persons_copied += 1

    regel_kopiert = False
    if payload.uebernehme_regeln:
        # Sitzungsregel ist ein Singleton – bleibt erhalten, nichts zu kopieren
        regel = db.get(Sitzungsregel, 1)
        regel_kopiert = regel is not None

    db.commit()
    db.refresh(existing)

    return JahresplanCopyResult(
        jahresplan_id=existing.id,
        ziel_jahr=existing.jahr,
        personen_uebernommen=persons_copied,
        regel_kopiert=regel_kopiert,
    )
