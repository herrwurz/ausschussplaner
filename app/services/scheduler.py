"""Berechnungs-Engine für Terminvorschläge (basierend auf perfektem Prompt).

Dieser Scheduler evaluiert ALLE möglichen (Wochentag, Zeitslot) Kombinationen
und gibt die besten Termine zurück, sortiert nach Qualität.

Kernidee:
1. Definiere alle möglichen Zeitslots mit ihren erforderlichen Verfügbarkeitsstunden
2. Für jeden (Wochentag, Slot) → evaluiere, welche Mitglieder verfügbar sind
3. Berechne: attendance, quorate, chair_present, etc.
4. Sortiere nach: fullAttendance > chairPresent > quorate > attendance
5. Gib Top-N Termine zurück
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, timedelta

from app.models.enums import AusschussTyp, Rolle, TerminStatus, Wochentag

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# ZEITSLOT-DEFINITIONEN
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class TimeSlot:
    """Ein möglicher Zeitslot für eine Sitzung (90 Min).

    start_time: "HH:MM"
    end_time: "HH:MM"
    required_availability_hours: List von DISKRETEN Verfügbarkeitsstunden
                                  (z.B. ["17:00", "18:00"] für 17:00-18:30)
    """
    start_time: str
    end_time: str
    required_availability_hours: list[str]


# Alle möglichen Zeitslots (90 Min duration).
# Fachliche Festlegung (2026-07): Die Randslots 07:00–08:30 und 19:00–20:30
# sind gültige Sitzungszeiten. Das Verfügbarkeits-Häkchen "07:00" bzw. "19:00"
# bedeutet "für den gesamten Früh-/Spätblock verfügbar" (die Matrix kennt
# keine 08:00/20:00-Stunden).
TIME_SLOTS = [
    TimeSlot("07:00", "08:30", ["07:00"]),
    TimeSlot("16:00", "17:30", ["16:00", "17:00"]),
    TimeSlot("16:30", "18:00", ["16:00", "17:00"]),
    TimeSlot("17:00", "18:30", ["17:00", "18:00"]),
    TimeSlot("17:30", "19:00", ["17:00", "18:00"]),
    TimeSlot("18:00", "19:30", ["18:00", "19:00"]),
    TimeSlot("18:30", "20:00", ["18:00", "19:00"]),
    TimeSlot("19:00", "20:30", ["19:00"]),
]

WEEKDAYS = [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]

WEEKDAY_SCORE = {
    Wochentag.MO: 1,
    Wochentag.DI: 2,
    Wochentag.MI: 3,
    Wochentag.DO: 4,
    Wochentag.FR: 5,
}

TIME_SCORE = {
    "07:00": 1,
    "16:00": 2,
    "16:30": 3,
    "17:00": 4,
    "17:30": 5,
    "18:00": 6,
    "18:30": 7,
    "19:00": 8,
}


# ═══════════════════════════════════════════════════════════════════════════
# INPUT/OUTPUT STRUKTUREN
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class MemberInput:
    """Ein Ausschussmitglied mit seiner Verfügbarkeit.

    availability: dict[Wochentag] -> set[str] von verfügbaren Stunden
                  z.B. {Wochentag.MO: {"16:00", "17:00", "18:00"}}
    absent_dates: frozenset[date] von Daten, an denen Person abwesend ist.
                  Abwesenheiten haben Vorrang vor Verfügbarkeit.
    """
    person_id: int
    name: str
    rolle: Rolle
    availability: dict[Wochentag, set[str]]
    absent_dates: frozenset[date] = field(default_factory=frozenset)


@dataclass(frozen=True)
class CommitteeInput:
    committee_id: int
    name: str
    typ: AusschussTyp
    members: list[MemberInput]
    quorum_override: int | None = None


@dataclass
class SlotEvaluation:
    """Evaluierung eines (Wochentag, Zeitslot) für einen Ausschuss."""
    committee_id: int
    committee_name: str
    week: int  # 1 oder 2
    weekday: Wochentag
    start_time: str
    end_time: str
    required_availability_hours: list[str]
    present_members: list[MemberInput]
    missing_members: list[MemberInput]
    attendance_count: int
    total_members: int
    attendance_rate: float
    chair_present: bool
    deputy_chair_present: bool
    quorate: bool
    full_attendance: bool

    @property
    def start_min(self) -> int:
        h, m = map(int, self.start_time.split(":"))
        return h * 60 + m

    @property
    def end_min(self) -> int:
        h, m = map(int, self.end_time.split(":"))
        return h * 60 + m

    @property
    def status(self) -> TerminStatus:
        """Bestimme Status basierend auf Verfügbarkeit (Spez SCHEDULING.md §6)."""
        if self.full_attendance:
            return TerminStatus.TOP
        if self.quorate:
            return TerminStatus.BESCHLUSSFAEHIG
        if self.chair_present and self.deputy_chair_present:
            return TerminStatus.ALTERNATIV
        if self.chair_present:
            return TerminStatus.OBMANN_DA
        return TerminStatus.NICHT_BESCHLUSSFAEHIG

    @property
    def quote(self) -> int:
        """Anwesenheitsquote in Prozent."""
        if self.total_members == 0:
            return 0
        return round(100 * self.attendance_rate)


# ═══════════════════════════════════════════════════════════════════════════
# KERNFUNKTIONEN
# ═══════════════════════════════════════════════════════════════════════════

def is_person_absent(person: MemberInput, meeting_date: date) -> bool:
    """Prüfe, ob Person am given Datum abwesend ist.

    Args:
        person: MemberInput mit absent_dates frozenset
        meeting_date: Datum des möglichen Termins

    Returns:
        True wenn Person abwesend, False sonst
    """
    return meeting_date in person.absent_dates


def is_person_available_for_slot(
    person: MemberInput,
    weekday: Wochentag,
    slot: TimeSlot,
    meeting_date: date | None = None,
) -> bool:
    """Prüfe, ob Person ALLE erforderlichen Stunden verfügbar hat.

    Abwesenheiten haben Vorrang: Wenn Person an meeting_date abwesend ist,
    return False sofort (auch wenn Verfügbarkeit sonst stimmt).

    Args:
        person: MemberInput
        weekday: Wochentag (Mo–Fr)
        slot: TimeSlot mit required_availability_hours
        meeting_date: Optionales Datum des Termins. Falls gegeben, prüfe Abwesenheit.

    Returns:
        True wenn Person für diesen Slot verfügbar ist, False sonst
    """
    if meeting_date is not None and is_person_absent(person, meeting_date):
        return False

    person_availability = person.availability.get(weekday, set())
    return all(hour in person_availability for hour in slot.required_availability_hours)


def is_quorate(
    committee: CommitteeInput,
    members: list[MemberInput],
    present_ids: set[int],
) -> bool:
    """Prüfe, ob Ausschuss beschlussfähig ist.

    Regeln:
    - STANDARD: Obmann MUSS anwesend sein + mind. 50% der Mitglieder
    - STADTRAT: ALLE Mitglieder müssen verfügbar sein
    - GEMEINDERAT: ALLE Mitglieder oder mind. 50% (mit Bürgermeisterin)
    - quorum_override (falls gesetzt): Obmann + mind. quorum_override Anwesende
      insgesamt (ersetzt die 50%-Regel, nicht die Obmann-Pflicht)
    """
    if not members:
        return False

    # Bürgermeisterin (Rolle: OBMANN) ist immer erforderlich
    chair = next((m for m in members if m.rolle == Rolle.OBMANN), None)
    if not chair or chair.person_id not in present_ids:
        return False

    # Spezielle Regeln nach Ausschusstyp
    if committee.typ == AusschussTyp.STADTRAT:
        # Alle Stadträte müssen verfügbar sein
        return len(present_ids) == len(members)

    if committee.typ == AusschussTyp.GEMEINDERAT:
        # Alle 33 Personen ODER mind. 50% + Bürgermeisterin
        return len(present_ids) == len(members) or len(present_ids) >= (len(members) / 2)

    # STANDARD: konfiguriertes Quorum hat Vorrang, sonst Obmann + mind. 50%
    if committee.quorum_override is not None:
        return len(present_ids) >= committee.quorum_override

    required = len(members) / 2
    return len(present_ids) >= required


def evaluate_committee_slots(
    committee: CommitteeInput,
    weeks: int = 2,
    start_date: date | None = None,
    freitag_modus: str = "reserve",
) -> list[SlotEvaluation]:
    """Evaluiere ALLE (Wochentag, Zeitslot, Woche) Kombinationen.

    Args:
        committee: CommitteeInput mit Mitgliedern
        weeks: Anzahl der Planungswochen (1–2)
        start_date: Montag der ersten Planungswoche. Falls gegeben, nutze für Abwesenheits-Checks.
        freitag_modus: "nein" = Freitag komplett ausschließen,
                       "reserve" = Freitag eine Prioritätsstufe schlechter (Default),
                       "normal" = Freitag gleichrangig (Abschlag bleibt als Tiebreak).

    Returns:
        Sortierte Liste von SlotEvaluation
    """
    weekdays = WEEKDAYS if freitag_modus != "nein" else [d for d in WEEKDAYS if d != Wochentag.FR]

    # Filtere nur echte Mitglieder (mit Rolle) und dedupliziere nach person_id
    # (dieselbe Person darf nicht doppelt fürs Quorum zählen; Masterprompt §1)
    real_members: list[MemberInput] = []
    seen_ids: set[int] = set()
    for m in committee.members:
        if m.rolle not in (Rolle.OBMANN, Rolle.OBMANN_STELLVERTRETER, Rolle.MITGLIED):
            continue
        if m.person_id in seen_ids:
            continue
        seen_ids.add(m.person_id)
        real_members.append(m)

    results: list[SlotEvaluation] = []

    # Für jede Woche
    for week in range(1, weeks + 1):
        # Für jeden Wochentag
        for weekday in weekdays:
            # Berechne Datum dieser Kombination (falls start_date gegeben)
            meeting_date = None
            if start_date is not None:
                weekday_offset = {
                    Wochentag.MO: 0,
                    Wochentag.DI: 1,
                    Wochentag.MI: 2,
                    Wochentag.DO: 3,
                    Wochentag.FR: 4,
                }
                days_offset = (week - 1) * 7 + weekday_offset[weekday]
                meeting_date = start_date + timedelta(days=days_offset)

            # Für jeden Zeitslot
            for slot in TIME_SLOTS:
                # Finde anwesende Mitglieder
                present = [m for m in real_members if is_person_available_for_slot(m, weekday, slot, meeting_date)]
                missing = [m for m in real_members if m not in present]
                present_ids = {m.person_id for m in present}

                # Bestimme Obmann/Stellvertreter
                chair = next((m for m in real_members if m.rolle == Rolle.OBMANN), None)
                deputy = next((m for m in real_members if m.rolle == Rolle.OBMANN_STELLVERTRETER), None)
                # "is not None and" statt "and": liefert immer echtes bool
                # (None würde Pydantic-Validierung von obmann_da/stv_da brechen)
                chair_present = chair is not None and chair.person_id in present_ids
                deputy_present = deputy is not None and deputy.person_id in present_ids

                # Bestimme Quorum
                quorate = is_quorate(committee, real_members, present_ids)

                # Erstelle Evaluation
                eval_result = SlotEvaluation(
                    committee_id=committee.committee_id,
                    committee_name=committee.name,
                    week=week,
                    weekday=weekday,
                    start_time=slot.start_time,
                    end_time=slot.end_time,
                    required_availability_hours=slot.required_availability_hours,
                    present_members=present,
                    missing_members=missing,
                    attendance_count=len(present),
                    total_members=len(real_members),
                    attendance_rate=len(present) / len(real_members) if real_members else 0,
                    chair_present=chair_present,
                    deputy_chair_present=deputy_present,
                    quorate=quorate,
                    # Leerer Ausschuss ist kein 100%-Termin (nach Copy ohne Mitglieder)
                    full_attendance=bool(real_members) and len(missing) == 0,
                )
                results.append(eval_result)

    # Sortiere nach Qualität
    return sort_evaluations(results)


def status_rank(e: SlotEvaluation) -> int:
    """Prioritätsstufe laut Spez (SCHEDULING.md §6) — niedriger ist besser.

    top(0) > beschlussfähig(2) > Obmann+Stv.(4) > nur Obmann(6) > Rest(8).
    Freitagstermine sind je eine Stufe schlechter (+1, freitag_modus 'reserve').
    """
    if e.full_attendance:
        rank = 0
    elif e.quorate:
        rank = 2
    elif e.chair_present and e.deputy_chair_present:
        rank = 4
    elif e.chair_present:
        rank = 6
    else:
        rank = 8
    if e.weekday == Wochentag.FR:
        rank += 1
    return rank


def priority_key(e: SlotEvaluation) -> tuple:
    """Zentrale Prioritätsfunktion — überall identisch verwenden.

    Reihenfolge: Statusstufe (inkl. Freitagsabschlag) → Anwesenheitszahl →
    Anwesenheitsquote → früher Wochentag → bevorzugte Uhrzeit.
    """
    return (
        status_rank(e),
        -e.attendance_count,
        -e.attendance_rate,
        WEEKDAY_SCORE[e.weekday],
        TIME_SCORE.get(e.start_time, 99),
    )


def sort_evaluations(results: list[SlotEvaluation]) -> list[SlotEvaluation]:
    """Sortiere nach Spez-Priorität: top > beschlussfähig > Obmann+Stv. > Obmann."""
    return sorted(results, key=priority_key)


# ═══════════════════════════════════════════════════════════════════════════
# GLOBALES SCHEDULING - Konflikt-Vermeidung
# ═══════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class OccupiedSlot:
    """Bereits belegter Zeitslot (fixierter Termin oder zugewiesener Vorschlag)."""
    week: int
    weekday: Wochentag
    start_time: str
    end_time: str
    person_ids: frozenset[int] = field(default_factory=frozenset)
    committee_id: int | None = None
    label: str = ""


@dataclass
class GlobalSchedule:
    """Globale Planung mit Konflikt-Erkennung."""
    assigned: dict[int, SlotEvaluation]  # committee_id -> assigned SlotEvaluation
    conflicts: list[str] = field(default_factory=list)


def _times_overlap(start1: str, end1: str, start2: str, end2: str) -> bool:
    """Prüfe ob zwei Zeitintervalle sich überschneiden."""
    def time_to_minutes(time_str: str) -> int:
        h, m = map(int, time_str.split(":"))
        return h * 60 + m

    start1_min = time_to_minutes(start1)
    end1_min = time_to_minutes(end1)
    start2_min = time_to_minutes(start2)
    end2_min = time_to_minutes(end2)
    return start1_min < end2_min and start2_min < end1_min


def _member_ids(e: SlotEvaluation) -> frozenset[int]:
    """Alle Mitglieder eines Slots (anwesend + fehlend)."""
    return frozenset(m.person_id for m in e.present_members) | frozenset(
        m.person_id for m in e.missing_members
    )


def _evaluation_to_occupied(e: SlotEvaluation) -> OccupiedSlot:
    return OccupiedSlot(
        week=e.week,
        weekday=e.weekday,
        start_time=e.start_time,
        end_time=e.end_time,
        person_ids=_member_ids(e),
        committee_id=e.committee_id,
        label=e.committee_name,
    )


def _slots_conflict(
    week: int,
    weekday: Wochentag,
    start: str,
    end: str,
    person_ids: frozenset[int],
    occupied: OccupiedSlot,
    *,
    member_aware: bool = True,
) -> bool:
    """Konflikt: gleiche Woche/Tag + Zeitüberlappung + (gemeinsame Personen oder Hard-Block)."""
    if occupied.week != week or occupied.weekday != weekday:
        return False
    if not _times_overlap(occupied.start_time, occupied.end_time, start, end):
        return False
    if not member_aware:
        return True
    # Leere person_ids = Hard-Block (z. B. unbekannte Besetzung)
    if not occupied.person_ids or not person_ids:
        return True
    return bool(occupied.person_ids & person_ids)


def _day_count(occupied: list[OccupiedSlot], week: int, weekday: Wochentag) -> int:
    return sum(1 for o in occupied if o.week == week and o.weekday == weekday)


def _option_allowed(
    option: SlotEvaluation,
    occupied: list[OccupiedSlot],
    max_per_day: int | None,
    *,
    member_aware: bool = True,
) -> bool:
    persons = _member_ids(option)
    for occ in occupied:
        if _slots_conflict(
            option.week, option.weekday, option.start_time, option.end_time,
            persons, occ, member_aware=member_aware,
        ):
            return False
    if max_per_day is not None and max_per_day > 0:
        if _day_count(occupied, option.week, option.weekday) >= max_per_day:
            return False
    return True


def _backtrack_schedule(
    committees: list[tuple],
    assigned: dict[int, SlotEvaluation],
    occupied: list[OccupiedSlot],
    index: int,
    max_per_day: int | None,
    member_aware: bool,
) -> bool:
    """Recursive backtracking to find conflict-free scheduling."""
    if index == len(committees):
        return True

    committee_id, evaluations = committees[index]

    week_counts: dict[int, int] = {}
    for occ in occupied:
        week_counts[occ.week] = week_counts.get(occ.week, 0) + 1

    sorted_options = sorted(
        evaluations,
        key=lambda e: (
            status_rank(e),
            week_counts.get(e.week, 0),
            -e.attendance_count,
            -e.attendance_rate,
            WEEKDAY_SCORE[e.weekday],
            TIME_SCORE.get(e.start_time, 99),
        ),
    )

    for option in sorted_options:
        if not _option_allowed(option, occupied, max_per_day, member_aware=member_aware):
            continue

        assigned[committee_id] = option
        occupied.append(_evaluation_to_occupied(option))

        if _backtrack_schedule(
            committees, assigned, occupied, index + 1, max_per_day, member_aware
        ):
            return True

        occupied.pop()
        del assigned[committee_id]

    return False


def global_schedule_committees(
    all_evaluations: dict[int, list[SlotEvaluation]],
    *,
    blocked: list[OccupiedSlot] | None = None,
    max_ausschuesse_pro_tag: int | None = None,
    member_aware: bool = True,
) -> GlobalSchedule:
    """Backtracking Scheduling mit optionalen Fix-Terminen und Tageslimit.

    Konflikt = Zeitüberlappung am selben Tag **und** gemeinsame Mitglieder
    (wenn member_aware=True). Fixierte Termine in `blocked` belegen Slots vorab.
    """
    skipped = [cid for cid, evals in all_evaluations.items() if not evals]
    if skipped:
        logger.warning("Ausschüsse ohne Terminoptionen (übersprungen): %s", skipped)

    sorted_committees = sorted(
        ((cid, evals) for cid, evals in all_evaluations.items() if evals),
        key=lambda x: len(x[1]),
    )

    seed = list(blocked or [])
    assigned: dict[int, SlotEvaluation] = {}
    occupied: list[OccupiedSlot] = list(seed)

    success = _backtrack_schedule(
        sorted_committees, assigned, occupied, 0,
        max_ausschuesse_pro_tag, member_aware,
    )
    logger.info(
        "Backtracking: %s – zugewiesen %d/%d Ausschüsse",
        "SUCCESS" if success else "FAILED", len(assigned), len(sorted_committees),
    )

    conflicts = [f"Ausschuss {cid}: keine Terminoptionen" for cid in skipped]
    if blocked:
        conflicts.extend(
            f"Fixiert: {b.label or b.committee_id} ({b.weekday.value} W{b.week} {b.start_time})"
            for b in blocked
        )

    if success:
        return GlobalSchedule(assigned=assigned, conflicts=conflicts)

    logger.warning("Backtracking fehlgeschlagen – Greedy-Fallback")
    assigned = {}
    occupied = list(seed)
    conflicts = [f"Ausschuss {cid}: keine Terminoptionen" for cid in skipped]

    for committee_id, evaluations in sorted_committees:
        sorted_options = sorted(evaluations, key=priority_key)
        placed = False
        for option in sorted_options:
            if _option_allowed(
                option, occupied, max_ausschuesse_pro_tag, member_aware=member_aware
            ):
                assigned[committee_id] = option
                occupied.append(_evaluation_to_occupied(option))
                placed = True
                break

        if not placed:
            assigned[committee_id] = sorted_options[0]
            occupied.append(_evaluation_to_occupied(sorted_options[0]))
            conflicts.append(
                f"Ausschuss {committee_id}: Terminüberschneidung nicht auflösbar"
            )

    return GlobalSchedule(assigned=assigned, conflicts=conflicts)


# ═══════════════════════════════════════════════════════════════════════════
# API (für calculation_service)
# ═══════════════════════════════════════════════════════════════════════════

def calculate_committee_dates(
    committees: list[CommitteeInput],
    weeks: int = 2,
    max_alternatives: int = 10,
    start_date: date | None = None,
    freitag_modus: str = "reserve",
) -> dict[int, list[SlotEvaluation]]:
    """Berechne beste Termine für alle Ausschüsse.

    Args:
        committees: Liste von CommitteeInput
        weeks: Anzahl der Planungswochen
        max_alternatives: Max. Anzahl Vorschläge pro Ausschuss
        start_date: Montag der ersten Planungswoche (optional, für Abwesenheits-Checks)
        freitag_modus: siehe evaluate_committee_slots

    Returns:
        dict[committee_id] -> list[SlotEvaluation] (top N)
    """
    result = {}
    for committee in committees:
        evaluations = evaluate_committee_slots(committee, weeks, start_date, freitag_modus)
        # Gib Top N Termine pro Ausschuss
        result[committee.committee_id] = evaluations[:max_alternatives]
    return result
