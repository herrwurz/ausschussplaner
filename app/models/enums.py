"""Enumerationen für das Datenmodell."""
from __future__ import annotations

import enum


class AusschussTyp(str, enum.Enum):
    """Ausschusstyp bestimmt die Beschlussfähigkeitsregel."""

    STANDARD = "standard"   # Obmann + min. 4 weitere
    POLY = "poly"           # Obmann + min. 2 weitere
    KONTROLL = "kontroll"   # Obmann + min. 3 weitere


class Rolle(str, enum.Enum):
    """Rolle einer Person in einem Ausschuss.

    WICHTIG (Masterprompt): Nur diese Rollen gelten als echtes Mitglied.
    Fehlt ein Eintrag oder steht '-', ist die Person KEIN Mitglied.
    """

    OBMANN = "Obmann"
    OBMANN_STELLVERTRETER = "Obmann Stellvertreter"
    MITGLIED = "Mitglied"


class Wochentag(str, enum.Enum):
    """Wochentage Mo–Fr (Sa/So nicht relevant für Sitzungen)."""

    MO = "Mo"
    DI = "Di"
    MI = "Mi"
    DO = "Do"
    FR = "Fr"


class AbwesenheitsArt(str, enum.Enum):
    """Art einer Abwesenheit."""

    URLAUB = "Urlaub"
    KRANKHEIT = "Krankheit"
    DIENSTREISE = "Dienstreise"
    ENTSCHULDIGT = "Entschuldigt"
    SONSTIGES = "Sonstiges"


class TerminStatus(str, enum.Enum):
    """Berechneter Status eines Terminvorschlags."""

    TOP = "top"                              # 100 % Anwesenheit
    BESCHLUSSFAEHIG = "beschlussfähig"       # Obmann + Quorum erfüllt
    ALTERNATIV = "alternativ"                # Obmann + Stv. da, aber unter Quorum
    OBMANN_DA = "obmann_da"                  # nur Obmann da
    NICHT_BESCHLUSSFAEHIG = "nicht_beschlussfähig"


class Partei(str, enum.Enum):
    """Österreichische Parteien."""

    SPOE = "SPÖ"
    OEVP = "ÖVP"
    GRUENE = "Die Grünen"
    FPOE = "FPÖ"
    NEOS = "NEOS"
    KPOE = "KPÖ"
