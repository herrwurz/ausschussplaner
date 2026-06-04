"""Pydantic-Schemas für Request-/Response-Validierung."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    AbwesenheitsArt,
    AusschussTyp,
    Rolle,
    TerminStatus,
    Wochentag,
)


# ─────────────────────────── Person ───────────────────────────
class PersonBase(BaseModel):
    vorname: str = Field(min_length=1, max_length=100)
    nachname: str = Field(min_length=1, max_length=100)
    titel: str = ""
    gremium: str = ""
    email: str = ""
    aktiv: bool = True


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    vorname: str | None = None
    nachname: str | None = None
    titel: str | None = None
    gremium: str | None = None
    email: str | None = None
    aktiv: bool | None = None


class PersonOut(PersonBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str


# ─────────────────────── Verfügbarkeit ────────────────────────
class VerfuegbarkeitItem(BaseModel):
    wochentag: Wochentag
    stunde: int = Field(ge=0, le=23)
    verfuegbar: bool = True


class VerfuegbarkeitBulk(BaseModel):
    """Komplette Verfügbarkeit einer Person als Liste setzen."""

    items: list[VerfuegbarkeitItem]


class VerfuegbarkeitOut(VerfuegbarkeitItem):
    model_config = ConfigDict(from_attributes=True)
    id: int
    person_id: int


# ───────────────────────── Ausschuss ──────────────────────────
class MitgliedItem(BaseModel):
    person_id: int
    rolle: Rolle


class AusschussBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    typ: AusschussTyp = AusschussTyp.STANDARD
    turnus: str = ""
    aktiv: bool = True
    quorum_override: int | None = None


class AusschussCreate(AusschussBase):
    mitglieder: list[MitgliedItem] = []


class AusschussUpdate(BaseModel):
    name: str | None = None
    typ: AusschussTyp | None = None
    turnus: str | None = None
    aktiv: bool | None = None
    quorum_override: int | None = None
    mitglieder: list[MitgliedItem] | None = None


class MitgliedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_id: int
    rolle: Rolle
    name: str


class AusschussOut(AusschussBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    mitglieder: list[MitgliedOut] = []


# ──────────────────────── Abwesenheit ─────────────────────────
class AbwesenheitBase(BaseModel):
    person_id: int
    von: date
    bis: date
    art: AbwesenheitsArt
    bemerkung: str = ""


class AbwesenheitCreate(AbwesenheitBase):
    pass


class AbwesenheitOut(AbwesenheitBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    person_name: str | None = None


# ─────────────────────── Sitzungsregel ────────────────────────
class SitzungsregelBase(BaseModel):
    block_minuten: int = 90
    sitzung_minuten: int = 75
    pause_minuten: int = 15
    council_minuten: int = 240
    quorum_standard: int = 4
    quorum_poly: int = 2
    quorum_kontroll: int = 3
    planungswochen: int = 2
    freitag_modus: str = "reserve"


class SitzungsregelOut(SitzungsregelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ───────────────────── Berechnung / Output ────────────────────
class BerechnungRequest(BaseModel):
    """Parameter für die Terminberechnung."""

    ausschuss_ids: list[int] | None = None  # None = alle aktiven
    planungswochen: int = 2
    freitag_modus: str = "reserve"  # reserve | normal | nein
    max_alternativen: int = 5


class TerminVorschlagOut(BaseModel):
    woche: int
    wochentag: Wochentag
    start: str          # "16:00"
    ende: str           # "17:30"
    ausschuss_id: int
    ausschuss_name: str
    obmann_da: bool
    stv_da: bool
    anwesend: int
    mitglieder: int
    quote: int
    status: TerminStatus
    empfehlung: str
    fehlende: list[str]


class AusschussAnalyse(BaseModel):
    """Vollständige Analyse a–f je Ausschuss."""

    ausschuss_id: int
    ausschuss_name: str
    typ: AusschussTyp
    mitglieder: list[MitgliedOut]
    top_termine: list[TerminVorschlagOut]
    beschlussfaehig: list[TerminVorschlagOut]
    alternativen: list[TerminVorschlagOut]
    beste_je_tag: list[TerminVorschlagOut]
    risiko: list[dict]
    empfehlung_text: str


class BerechnungResponse(BaseModel):
    analysen: list[AusschussAnalyse]
    zusammenfassung: dict


# ─────────────────────── Jahresplan ───────────────────────────
class JahresplanCopy(BaseModel):
    quelle_jahr: int
    ziel_jahr: int
    uebernehme_verfuegbarkeiten: bool = True
    uebernehme_regeln: bool = True
    schliesse_inaktive_aus: bool = False


# ─────────────────── Agenden-Übernahme / Nachfolge ────────────────────
class AgendaTransfer(BaseModel):
    """Überträgt alle Ausschuss-Mitgliedschaften (Agenden) von einer Person
    auf eine andere. Typischer Fall: ausgeschiedenes Mandat wird ersetzt.
    """

    von_person_id: int
    zu_person_id: int
    quelle_deaktivieren: bool = True   # ausscheidende Person inaktiv setzen
    verfuegbarkeit_uebernehmen: bool = False  # optional Verfügbarkeit kopieren


class AgendaTransferResult(BaseModel):
    von_person_id: int
    zu_person_id: int
    uebertragene_mitgliedschaften: int
    uebersprungen: int   # bereits vorhandene Mitgliedschaften
    quelle_deaktiviert: bool
    verfuegbarkeit_kopiert: bool
