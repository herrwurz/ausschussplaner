"""Geschäftslogik für Jahresplan-Verwaltung: Anlegen, Auflisten, Kopieren."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.models import (
    Jahresplan,
    Sitzungsregel,
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
    """Legt einen Jahresplan für das Zieljahr an (falls nötig).

    Verfügbarkeiten sind personenbezogen bzw. perioden-spezifisch — ein
    jahr-basiertes Kopieren ist hier nicht sinnvoll und wird bewusst nicht
    als Erfolgsfall gemeldet (personen_uebernommen=0).
    """
    existing = db.scalars(
        select(Jahresplan).where(Jahresplan.jahr == payload.ziel_jahr)
    ).first()
    if existing is None:
        existing = Jahresplan(jahr=payload.ziel_jahr, bezeichnung=f"Kopie von {payload.quelle_jahr}")
        db.add(existing)
        db.flush()

    # Sitzungsregel ist Singleton — nichts zu kopieren
    regel = db.get(Sitzungsregel, 1) if payload.uebernehme_regeln else None

    db.commit()
    db.refresh(existing)

    return JahresplanCopyResult(
        jahresplan_id=existing.id,
        ziel_jahr=existing.jahr,
        personen_uebernommen=0,
        regel_kopiert=regel is not None,
    )
