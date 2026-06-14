"""Berechnungs-Engine für Terminvorschläge (Masterprompt-konform).

Die Engine ist bewusst frei von DB-Abhängigkeiten, damit sie isoliert
getestet werden kann. Sie arbeitet mit einfachen Dataclasses und reinem
Python. Der Service-Layer (calculation_service) füttert sie aus der DB.

Kernregeln (Masterprompt):
1. Mitgliedsdefinition: Nur Personen mit echter Rolle zählen.
2. Stundenbasis: Verfügbarkeit in vollen Stunden; gesamter Block muss
   abgedeckt sein.
3. Starts: volle ODER halbe Stunde.
4. Beschlussfähigkeit: Obmann + Mindestanzahl weiterer Mitglieder je Typ.
5. Priorität: 100 % > beschlussfähig > Obmann+Stv. > Obmann > nichts.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models.enums import AusschussTyp, Rolle, TerminStatus, Wochentag

DAYS: list[Wochentag] = [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]
DAY_LABEL = {
    Wochentag.MO: "Montag",
    Wochentag.DI: "Dienstag",
    Wochentag.MI: "Mittwoch",
    Wochentag.DO: "Donnerstag",
    Wochentag.FR: "Freitag",
}
DAY_OFFSET: dict[Wochentag, int] = {
    Wochentag.MO: 0,
    Wochentag.DI: 1,
    Wochentag.MI: 2,
    Wochentag.DO: 3,
    Wochentag.FR: 4,
}


# ───────────────────────── Eingabe-Strukturen ─────────────────────────
@dataclass(frozen=True)
class MemberInput:
    """Ein Mitglied mit Rolle und seiner Verfügbarkeit.

    availability: Mapping Wochentag -> Set verfügbarer voller Stunden.
    absent_dates: Konkrete Kalender-Daten, an denen die Person abwesend ist.
    """

    person_id: int
    name: str
    rolle: Rolle
    availability: dict[Wochentag, set[int]]
    absent_dates: frozenset = field(default_factory=frozenset)


@dataclass(frozen=True)
class CommitteeInput:
    committee_id: int
    name: str
    typ: AusschussTyp
    members: list[MemberInput]
    quorum_override: int | None = None


# ───────────────────────── Ergebnis-Strukturen ────────────────────────
@dataclass
class Slot:
    """Ein berechneter Terminvorschlag."""

    week: int
    day: Wochentag
    start_min: int
    end_min: int
    present: list[MemberInput]
    missing: list[MemberInput]
    obmann_present: bool
    stv_present: bool
    quote: int
    status: TerminStatus
    prio: int
    committee_id: int
    committee_name: str
    datum: date | None = None

    @property
    def start_str(self) -> str:
        return _fmt(self.start_min)

    @property
    def end_str(self) -> str:
        return _fmt(self.end_min)

    @property
    def empfehlung(self) -> str:
        return {
            TerminStatus.TOP: "Fixieren",
            TerminStatus.BESCHLUSSFAEHIG: "Empfohlen",
            TerminStatus.ALTERNATIV: "Flexibel",
            TerminStatus.OBMANN_DA: "Flexibel",
            TerminStatus.NICHT_BESCHLUSSFAEHIG: "Kritisch",
        }[self.status]


@dataclass
class CommitteeResult:
    committee: CommitteeInput
    members: list[MemberInput]
    all_slots: list[Slot] = field(default_factory=list)
    best_per_day: list[Slot] = field(default_factory=list)
    min_extra: int = 4


# ───────────────────────── Hilfsfunktionen ────────────────────────────
def _fmt(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def required_hours(start_min: int, duration_min: int) -> list[int]:
    """Nur die Startstunde zählt.

    Wenn jemand "Stunde 19 verfügbar" ist, kann die Sitzung 19:00–20:30 stattfinden.
    19:00–19:30 ist Stunde 19, 19:30–20:30 ist auch noch Stunde 19.

    16:00–17:30 (start=960) -> [16]
    19:00–20:30 (start=1140) -> [19]
    """
    start_hour = start_min // 60
    return [start_hour]


def is_present(
    member: MemberInput,
    day: Wochentag,
    start_min: int,
    duration_min: int,
    slot_date: date | None = None,
) -> bool:
    """Person ist anwesend, wenn ALLE benötigten Stunden verfügbar und kein Abwesenheitseintrag für das Datum vorliegt."""
    if slot_date is not None and slot_date in member.absent_dates:
        return False
    avail = member.availability.get(day, set())
    return all(h in avail for h in required_hours(start_min, duration_min))


def allowed_starts(earliest_hour: int = 7, latest_hour: int = 19) -> list[int]:
    """Erlaubte Startzeiten: volle + halbe Stunden."""
    starts: list[int] = []
    for h in range(earliest_hour, latest_hour + 1):
        starts.append(h * 60)
        if h < latest_hour:
            starts.append(h * 60 + 30)
    return starts


def _is_obmann(rolle: Rolle) -> bool:
    return rolle == Rolle.OBMANN


def _is_stv(rolle: Rolle) -> bool:
    return rolle == Rolle.OBMANN_STELLVERTRETER


def quorum_for(typ: AusschussTyp, defaults: dict[AusschussTyp, int], override: int | None) -> int:
    if override is not None:
        return override
    return defaults.get(typ, defaults[AusschussTyp.STANDARD])


# ───────────────────────── Hauptberechnung ────────────────────────────
def calculate_committee(
    committee: CommitteeInput,
    *,
    duration_min: int = 90,
    weeks: int = 2,
    friday_mode: str = "reserve",
    max_alternatives: int = 5,
    quorum_defaults: dict[AusschussTyp, int] | None = None,
    max_end_min: int = 20 * 60 + 30,
    start_date: date | None = None,
) -> CommitteeResult:
    """Berechne alle Terminvorschläge eines Ausschusses."""
    if quorum_defaults is None:
        quorum_defaults = {
            AusschussTyp.STANDARD: 4,
            AusschussTyp.POLY: 2,
            AusschussTyp.KONTROLL: 3,
        }

    # 1. Nur echte Mitglieder, dedupliziert
    seen: set[int] = set()
    members: list[MemberInput] = []
    for m in committee.members:
        if m.person_id in seen:
            continue
        seen.add(m.person_id)
        members.append(m)

    obmann = next((m for m in members if _is_obmann(m.rolle)), None)
    stv = next((m for m in members if _is_stv(m.rolle)), None)
    min_extra = quorum_for(committee.typ, quorum_defaults, committee.quorum_override)

    all_slots: list[Slot] = []
    for week in range(1, weeks + 1):
        for day in DAYS:
            if day == Wochentag.FR and friday_mode == "nein":
                continue
            is_friday = day == Wochentag.FR

            slot_date: date | None = None
            if start_date is not None:
                slot_date = start_date + timedelta(days=(week - 1) * 7 + DAY_OFFSET[day])

            for start_min in allowed_starts():
                if start_min + duration_min > max_end_min:
                    continue

                present = [
                    m for m in members
                    if is_present(m, day, start_min, duration_min, slot_date)
                ]
                present_ids = {m.person_id for m in present}
                missing = [m for m in members if m.person_id not in present_ids]

                obmann_present = obmann is not None and obmann.person_id in present_ids
                stv_present = stv is not None and stv.person_id in present_ids
                extra_present = sum(1 for m in present if not _is_obmann(m.rolle))
                beschlussfaehig = obmann_present and extra_present >= min_extra
                quote = round(len(present) / len(members) * 100) if members else 0

                status, prio = _classify(
                    quote, beschlussfaehig, obmann_present, stv_present, is_friday
                )

                all_slots.append(
                    Slot(
                        week=week,
                        day=day,
                        start_min=start_min,
                        end_min=start_min + duration_min,
                        present=present,
                        missing=missing,
                        obmann_present=obmann_present,
                        stv_present=stv_present,
                        quote=quote,
                        status=status,
                        prio=prio,
                        committee_id=committee.committee_id,
                        committee_name=committee.name,
                        datum=slot_date,
                    )
                )

    all_slots.sort(key=lambda s: (s.prio, s.week, DAYS.index(s.day), s.start_min))

    # Beste Option je (Woche, Tag)
    seen_days: set[tuple[int, Wochentag]] = set()
    best: list[Slot] = []
    for s in all_slots:
        key = (s.week, s.day)
        if key not in seen_days:
            seen_days.add(key)
            best.append(s)
        if len(best) >= max_alternatives:
            break

    return CommitteeResult(
        committee=committee,
        members=members,
        all_slots=all_slots,
        best_per_day=best,
        min_extra=min_extra,
    )


def _classify(
    quote: int, beschlussfaehig: bool, obmann_present: bool, stv_present: bool, is_friday: bool
) -> tuple[TerminStatus, int]:
    """Status + Priorität (niedriger = besser)."""
    if quote == 100:
        return TerminStatus.TOP, 2 if is_friday else 1
    if beschlussfaehig:
        return TerminStatus.BESCHLUSSFAEHIG, 4 if is_friday else 3
    if obmann_present and stv_present:
        return TerminStatus.ALTERNATIV, 6 if is_friday else 5
    if obmann_present:
        return TerminStatus.OBMANN_DA, 7
    return TerminStatus.NICHT_BESCHLUSSFAEHIG, 9


def risk_analysis(result: CommitteeResult) -> list[dict]:
    """Wer blockiert wie viele Termine (als nicht beschlussfähig)?"""
    out: list[dict] = []
    for m in result.members:
        blocked = sum(
            1
            for s in result.all_slots
            if s.status == TerminStatus.NICHT_BESCHLUSSFAEHIG
            and any(x.person_id == m.person_id for x in s.missing)
        )
        level = "Kritisch" if blocked > 5 else "Risiko mittel" if blocked > 2 else "Gering"
        out.append(
            {"person_id": m.person_id, "name": m.name, "rolle": m.rolle.value,
             "blockiert": blocked, "stufe": level}
        )
    out.sort(key=lambda x: -x["blockiert"])
    return out


def recommendation_text(result: CommitteeResult) -> str:
    tops = [s for s in result.all_slots if s.status == TerminStatus.TOP]
    besch = [s for s in result.all_slots if s.status == TerminStatus.BESCHLUSSFAEHIG]
    if tops:
        picks = " · ".join(f"W{s.week} {DAY_LABEL[s.day]} {s.start_str}" for s in tops[:3])
        return f"Fixieren: {picks} — 100 % Anwesenheit gesichert."
    if besch:
        picks = " · ".join(f"W{s.week} {DAY_LABEL[s.day]} {s.start_str}" for s in besch[:2])
        return f"Empfohlen (Flexibel): {picks} — beschlussfähig."
    return "Kritisch: Kein beschlussfähiger Termin gefunden. Verfügbarkeiten prüfen oder Zeitraum erweitern."
