"""SQLAlchemy ORM-Modelle für das Terminplanungs-Datenmodell.

Datenmodell-Übersicht:
    Person          – Stammdaten einer Person + Gremium
    Verfuegbarkeit  – Standardverfügbarkeit je Person/Wochentag/Stunde
    Ausschuss       – Ausschuss mit Typ (bestimmt Quorum)
    Mitgliedschaft  – Verknüpfung Person↔Ausschuss mit Rolle
    Abwesenheit     – datierte Ausnahmen (Urlaub etc.)
    Sitzungsregel   – globale + ausschussspezifische Regeln
    Jahresplan      – Container zum Kopieren/Versionieren
    Sitzungsvorschlag – persistierte Berechnungsergebnisse
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import (
    AbwesenheitsArt,
    AusschussTyp,
    Rolle,
    TerminStatus,
    Wochentag,
)


class Person(Base):
    """Eine planbare Person (Stadtrat, Gemeinderat, Bürgermeister:in …)."""

    __tablename__ = "person"

    id: Mapped[int] = mapped_column(primary_key=True)
    vorname: Mapped[str] = mapped_column(String(100))
    nachname: Mapped[str] = mapped_column(String(100))
    titel: Mapped[str] = mapped_column(String(50), default="")
    gremium: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    verfuegbarkeiten: Mapped[list[Verfuegbarkeit]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    mitgliedschaften: Mapped[list[Mitgliedschaft]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )
    abwesenheiten: Mapped[list[Abwesenheit]] = relationship(
        back_populates="person", cascade="all, delete-orphan"
    )

    @property
    def name(self) -> str:
        teile = [self.titel, self.vorname, self.nachname]
        return " ".join(t for t in teile if t)


class Verfuegbarkeit(Base):
    """Standardverfügbarkeit: Person ist an Wochentag zur Stunde verfügbar.

    Stunden werden als volle Stunde gespeichert (z. B. 7, 16, 17, 18, 19).
    Ein Eintrag bedeutet 'verfügbar'; fehlt der Eintrag, gilt 'nicht verfügbar'.
    """

    __tablename__ = "verfuegbarkeit"
    __table_args__ = (
        UniqueConstraint("person_id", "wochentag", "stunde", name="uq_verfuegbarkeit"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    wochentag: Mapped[Wochentag] = mapped_column(Enum(Wochentag))
    stunde: Mapped[int] = mapped_column(Integer)  # 0–23
    verfuegbar: Mapped[bool] = mapped_column(Boolean, default=True)

    person: Mapped[Person] = relationship(back_populates="verfuegbarkeiten")


class Ausschuss(Base):
    """Ein Ausschuss; der Typ bestimmt die Beschlussfähigkeit."""

    __tablename__ = "ausschuss"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), unique=True)
    typ: Mapped[AusschussTyp] = mapped_column(Enum(AusschussTyp), default=AusschussTyp.STANDARD)
    turnus: Mapped[str] = mapped_column(String(50), default="")
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)

    # Optional pro Ausschuss überschreibbares Quorum (sonst Default je Typ)
    quorum_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    mitgliedschaften: Mapped[list[Mitgliedschaft]] = relationship(
        back_populates="ausschuss", cascade="all, delete-orphan"
    )


class Mitgliedschaft(Base):
    """Verknüpfung Person↔Ausschuss mit konkreter Rolle.

    Existiert ein Mitgliedschaftsdatensatz mit gültiger Rolle, gilt die Person
    als echtes Ausschussmitglied (Masterprompt-Definition).
    """

    __tablename__ = "mitgliedschaft"
    __table_args__ = (
        UniqueConstraint("person_id", "ausschuss_id", name="uq_mitgliedschaft"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    ausschuss_id: Mapped[int] = mapped_column(ForeignKey("ausschuss.id", ondelete="CASCADE"))
    rolle: Mapped[Rolle] = mapped_column(Enum(Rolle))

    person: Mapped[Person] = relationship(back_populates="mitgliedschaften")
    ausschuss: Mapped[Ausschuss] = relationship(back_populates="mitgliedschaften")


class Abwesenheit(Base):
    """Datierte Abwesenheit (überschreibt Standardverfügbarkeit im Zeitraum)."""

    __tablename__ = "abwesenheit"

    id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    von: Mapped[date] = mapped_column(Date)
    bis: Mapped[date] = mapped_column(Date)
    art: Mapped[AbwesenheitsArt] = mapped_column(Enum(AbwesenheitsArt))
    bemerkung: Mapped[str] = mapped_column(String(300), default="")

    person: Mapped[Person] = relationship(back_populates="abwesenheiten")


class Sitzungsregel(Base):
    """Globale Konfiguration der Berechnung (Singleton, id=1)."""

    __tablename__ = "sitzungsregel"

    id: Mapped[int] = mapped_column(primary_key=True)
    block_minuten: Mapped[int] = mapped_column(Integer, default=90)
    sitzung_minuten: Mapped[int] = mapped_column(Integer, default=75)
    pause_minuten: Mapped[int] = mapped_column(Integer, default=15)
    council_minuten: Mapped[int] = mapped_column(Integer, default=240)
    quorum_standard: Mapped[int] = mapped_column(Integer, default=4)
    quorum_poly: Mapped[int] = mapped_column(Integer, default=2)
    quorum_kontroll: Mapped[int] = mapped_column(Integer, default=3)
    planungswochen: Mapped[int] = mapped_column(Integer, default=2)
    freitag_modus: Mapped[str] = mapped_column(String(20), default="reserve")


class Jahresplan(Base):
    """Versionscontainer; ermöglicht Kopieren des Vorjahres."""

    __tablename__ = "jahresplan"

    id: Mapped[int] = mapped_column(primary_key=True)
    jahr: Mapped[int] = mapped_column(Integer)
    bezeichnung: Mapped[str] = mapped_column(String(150), default="")
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Sitzungsvorschlag(Base):
    """Persistiertes Ergebnis einer Terminberechnung."""

    __tablename__ = "sitzungsvorschlag"

    id: Mapped[int] = mapped_column(primary_key=True)
    ausschuss_id: Mapped[int] = mapped_column(ForeignKey("ausschuss.id", ondelete="CASCADE"))
    woche: Mapped[int] = mapped_column(Integer)
    wochentag: Mapped[Wochentag] = mapped_column(Enum(Wochentag))
    start_minute: Mapped[int] = mapped_column(Integer)
    end_minute: Mapped[int] = mapped_column(Integer)
    anwesend_count: Mapped[int] = mapped_column(Integer)
    mitglieder_count: Mapped[int] = mapped_column(Integer)
    quote: Mapped[int] = mapped_column(Integer)
    obmann_da: Mapped[bool] = mapped_column(Boolean)
    stv_da: Mapped[bool] = mapped_column(Boolean)
    status: Mapped[TerminStatus] = mapped_column(Enum(TerminStatus))
    fehlende: Mapped[str] = mapped_column(String(1000), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    ausschuss: Mapped[Ausschuss] = relationship()
