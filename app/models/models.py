"""SQLAlchemy ORM-Modelle für das Terminplanungs-Datenmodell.

Datenmodell-Übersicht:
    Gemeinderatsperiode – 5-Jahres-Periode (z.B. P1 2025-2029)
    PeriodePerson       – Zuordnung Person zu Periode mit Gültigkeitsdatum
    Person              – Stammdaten einer Person + Gremium
    Verfuegbarkeit      – Standardverfügbarkeit je Person/Wochentag/Stunde
    Ausschuss           – Ausschuss mit Typ (bestimmt Quorum), gehört zu Periode
    Mitgliedschaft      – Verknüpfung Person↔Ausschuss mit Rolle, mit Periode
    Abwesenheit         – datierte Ausnahmen (Urlaub etc.)
    Sitzungsregel       – globale + ausschussspezifische Regeln
    Jahresplan          – Container zum Kopieren/Versionieren, mit Periode
    Sitzungsvorschlag   – persistierte Berechnungsergebnisse
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
    Partei,
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
    partei: Mapped[str | None] = mapped_column(String(50), nullable=True)
    gremium: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    invite_expires: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
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
    """Ein Ausschuss; der Typ bestimmt die Beschlussfähigkeit. Gehört zu einer Gemeinderatsperiode."""

    __tablename__ = "ausschuss"

    id: Mapped[int] = mapped_column(primary_key=True)
    periode_id: Mapped[int | None] = mapped_column(ForeignKey("gemeinderatsperiode.id", ondelete="CASCADE"), nullable=True)
    name: Mapped[str] = mapped_column(String(150))
    typ: Mapped[AusschussTyp] = mapped_column(Enum(AusschussTyp), default=AusschussTyp.STANDARD)
    turnus: Mapped[str] = mapped_column(String(50), default="")
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)

    # Optional pro Ausschuss überschreibbares Quorum (sonst Default je Typ)
    quorum_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    periode: Mapped[Gemeinderatsperiode | None] = relationship(back_populates="ausschuesse")
    mitgliedschaften: Mapped[list[Mitgliedschaft]] = relationship(
        back_populates="ausschuss", cascade="all, delete-orphan"
    )


class Mitgliedschaft(Base):
    """Verknüpfung Person↔Ausschuss mit konkreter Rolle innerhalb einer Periode.

    Existiert ein Mitgliedschaftsdatensatz mit gültiger Rolle, gilt die Person
    als echtes Ausschussmitglied (Masterprompt-Definition).
    """

    __tablename__ = "mitgliedschaft"
    __table_args__ = (
        UniqueConstraint("periode_id", "person_id", "ausschuss_id", name="uq_mitgliedschaft_periode"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    periode_id: Mapped[int | None] = mapped_column(ForeignKey("gemeinderatsperiode.id", ondelete="CASCADE"), nullable=True)
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    ausschuss_id: Mapped[int] = mapped_column(ForeignKey("ausschuss.id", ondelete="CASCADE"))
    rolle: Mapped[Rolle] = mapped_column(Enum(Rolle))

    periode: Mapped[Gemeinderatsperiode | None] = relationship()
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
    """Versionscontainer pro Jahr einer Periode; ermöglicht Kopieren des Vorjahres.

    Eine Periode 2025-2029 hat mindestens 5 Jahrespläne (2025, 2026, 2027, 2028, 2029).
    Falls personelle Änderungen → zusätzlicher Jahresplan mit neuer Zusammensetzung.
    """

    __tablename__ = "jahresplan"

    id: Mapped[int] = mapped_column(primary_key=True)
    periode_id: Mapped[int | None] = mapped_column(ForeignKey("gemeinderatsperiode.id", ondelete="CASCADE"), nullable=True)
    jahr: Mapped[int] = mapped_column(Integer)
    bezeichnung: Mapped[str] = mapped_column(String(150), default="")
    variante: Mapped[int] = mapped_column(Integer, default=1)  # Variante bei Personenwechsel (1, 2, 3...)
    grund_variante: Mapped[str] = mapped_column(String(255), default="")  # z.B. "Nachbesetzung Müller"
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    periode: Mapped[Gemeinderatsperiode | None] = relationship(back_populates="jahresplaene")


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


class Gemeinderatsperiode(Base):
    """Eine 5-Jahres-Gemeinderatsperiode (z.B. P1 2025-2029)."""

    __tablename__ = "gemeinderatsperiode"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)  # z.B. "P1"
    start_jahr: Mapped[int] = mapped_column(Integer)  # 2025
    end_jahr: Mapped[int] = mapped_column(Integer)  # 2029
    aktiv: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    personen: Mapped[list[PeriodePerson]] = relationship(
        back_populates="periode", cascade="all, delete-orphan"
    )
    ausschuesse: Mapped[list[Ausschuss]] = relationship(
        back_populates="periode", cascade="all, delete-orphan"
    )
    jahresplaene: Mapped[list[Jahresplan]] = relationship(
        back_populates="periode", cascade="all, delete-orphan"
    )

    def __str__(self) -> str:
        return f"{self.name} {self.start_jahr}-{self.end_jahr}"


class PeriodePerson(Base):
    """Zuordnung: Person ist in einer Periode Mitglied (mit Start/End-Datum)."""

    __tablename__ = "periode_person"
    __table_args__ = (
        UniqueConstraint("periode_id", "person_id", name="uq_periode_person"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    periode_id: Mapped[int] = mapped_column(ForeignKey("gemeinderatsperiode.id", ondelete="CASCADE"))
    person_id: Mapped[int] = mapped_column(ForeignKey("person.id", ondelete="CASCADE"))
    start_datum: Mapped[date] = mapped_column(Date)  # Wann tritt Person bei
    end_datum: Mapped[date | None] = mapped_column(Date, nullable=True)  # Wann scheidet Person aus (None = noch aktiv)
    grund_austritt: Mapped[str] = mapped_column(String(255), default="")  # z.B. "Rücktritt", "Mandate abgelaufen"
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    periode: Mapped[Gemeinderatsperiode] = relationship(back_populates="personen")
    person: Mapped[Person] = relationship()
