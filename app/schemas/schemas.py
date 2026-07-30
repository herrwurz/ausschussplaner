"""Pydantic-Schemas für Request-/Response-Validierung."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    AbwesenheitsArt,
    AusschussTyp,
    Partei,
    Rolle,
    TerminStatus,
    Wochentag,
)


# ─────────────────────────── Periode ───────────────────────────
class PeriodeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    start_jahr: int
    end_jahr: int
    aktiv: bool


# ─────────────────────────── Jahresplan ───────────────────────────
class JahresplanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    jahr: int
    bezeichnung: str
    aktiv: bool


class JahresplanCreate(BaseModel):
    jahr: int
    bezeichnung: str = ""


class JahresplanUpdate(BaseModel):
    jahr: int | None = None
    bezeichnung: str | None = None


class JahresplanCopyResult(BaseModel):
    jahresplan_id: int
    ziel_jahr: int
    personen_uebernommen: int
    regel_kopiert: bool


# ─────────────────────────── Person ───────────────────────────
class PersonBase(BaseModel):
    vorname: str = Field(min_length=1, max_length=100)
    nachname: str = Field(min_length=1, max_length=100)
    titel: str = ""
    partei: Partei | None = None
    gremium: str = ""
    email: str = ""
    aktiv: bool = True


class PersonCreate(PersonBase):
    pass


class PersonUpdate(BaseModel):
    vorname: str | None = None
    nachname: str | None = None
    titel: str | None = None
    partei: Partei | None = None
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
    # float: DB speichert auch halbe Stunden (16.5, 17.5, ...) — int würde
    # GET/PUT für alle Personen mit solchen Einträgen mit 500 crashen
    stunde: float = Field(ge=0, le=23.5)
    verfuegbar: bool = True


class VerfuegbarkeitBulk(BaseModel):
    """Komplette Verfügbarkeit einer Person als Liste setzen."""

    items: list[VerfuegbarkeitItem]


class VerfuegbarkeitOut(VerfuegbarkeitItem):
    model_config = ConfigDict(from_attributes=True)
    id: int
    person_id: int
    periode_id: int | None = None  # None = Standard (alle Perioden)


# ───────────────────────── Ausschuss ──────────────────────────
class MitgliedItem(BaseModel):
    person_id: int
    rolle: Rolle


class AusschussBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    typ: AusschussTyp = AusschussTyp.STANDARD
    turnus: str = ""
    aktiv: bool = True


class AusschussCreate(AusschussBase):
    mitglieder: list[MitgliedItem] = []


class AusschussUpdate(BaseModel):
    name: str | None = None
    typ: AusschussTyp | None = None
    turnus: str | None = None
    aktiv: bool | None = None
    periode_id: int | None = None
    mitglieder: list[MitgliedItem] | None = None


class MitgliedOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_id: int
    rolle: Rolle
    name: str


class AusschussOut(AusschussBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    periode_id: int | None = None
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
    planungswochen: int = 2
    freitag_modus: str = "reserve"
    max_ausschuesse_pro_tag: int = 2


class SitzungsregelOut(SitzungsregelBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


# ───────────────────── Berechnung / Output ────────────────────
class BerechnungRequest(BaseModel):
    """Parameter für die Terminberechnung."""

    periode_id: int | None = None
    ausschuss_ids: list[int] | None = None  # None = alle aktiven
    planungswochen: int = 2
    freitag_modus: str = "reserve"  # reserve | normal | nein
    max_alternativen: int = 5
    min_verfuegbarkeit: int = 100  # 0-100, nur Termine mit mind. dieser Quote
    start_datum: date | None = None  # Montag der ersten Planungswoche; aktiviert Abwesenheits-Check
    max_ausschuesse_pro_tag: int = 2  # Maximum Ausschüsse pro Wochentag


class MitgliedDetail(BaseModel):
    """Mitglied mit seiner Rolle für die Detailanzeige."""
    name: str
    rolle: Rolle


class TerminVorschlagOut(BaseModel):
    woche: int
    wochentag: Wochentag
    start: str          # "16:00"
    ende: str           # "17:30"
    datum: date | None = None
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
    # Neue Validierungsdaten:
    required_availability_hours: list[str] = []  # z.B. ["17:00", "18:00"]
    anwesende_mitglieder: list[MitgliedDetail] = []  # wer ist verfügbar
    fehlende_mitglieder: list[MitgliedDetail] = []  # wer fehlt


class AusschussAnalyse(BaseModel):
    """Vollständige Analyse a–f je Ausschuss."""

    ausschuss_id: int
    ausschuss_name: str
    ausschuss_typ: AusschussTyp | None = None
    mitglieder: list[MitgliedOut] = []
    top_termine: list[TerminVorschlagOut] = []
    beschlussfaehig: list[TerminVorschlagOut] = []
    alternativen: list[TerminVorschlagOut] = []
    beste_je_tag: list[TerminVorschlagOut] = []
    risiko: list[dict] = []
    empfehlung_text: str = ""


class BerechnungResponse(BaseModel):
    analysen: list[AusschussAnalyse]
    start_datum: date | None = None
    planungswochen: int = 2
    zusammenfassung: dict | None = None
    timestamp: str | None = None


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


# ─────────────────── Sitzungsvorschlag (Persistierung) ────────────────
class SitzungsvorschlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ausschuss_id: int
    woche: int
    wochentag: Wochentag
    start_minute: int
    end_minute: int
    anwesend_count: int
    mitglieder_count: int
    quote: int
    obmann_da: bool
    stv_da: bool
    status: TerminStatus
    fehlende: str
    planungs_start_datum: date | None = None
