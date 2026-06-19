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

from dataclasses import dataclass, field
from datetime import date, timedelta
from enum import Enum

from app.models.enums import AusschussTyp, Rolle, TerminStatus, Wochentag


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


# Alle möglichen Zeitslots (90 Min duration)
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
        """Bestimme Status basierend auf Verfügbarkeit."""
        if self.full_attendance:
            return TerminStatus.TOP
        if self.quorate:
            return TerminStatus.BESCHLUSSFAEHIG
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

    Regel: Obmann MUSS anwesend sein + mind. 50% der Mitglieder.
    """
    if not members:
        return False

    # Obmann MUSS anwesend sein
    chair = next((m for m in members if m.rolle == Rolle.OBMANN), None)
    if not chair or chair.person_id not in present_ids:
        return False

    # Mind. 50% aller Mitglieder (einschließlich Obmann)
    required = len(members) / 2
    return len(present_ids) >= required


def evaluate_committee_slots(
    committee: CommitteeInput,
    weeks: int = 2,
    start_date: date | None = None,
) -> list[SlotEvaluation]:
    """Evaluiere ALLE (Wochentag, Zeitslot, Woche) Kombinationen.

    Args:
        committee: CommitteeInput mit Mitgliedern
        weeks: Anzahl der Planungswochen (1–2)
        start_date: Montag der ersten Planungswoche. Falls gegeben, nutze für Abwesenheits-Checks.

    Returns:
        Sortierte Liste von SlotEvaluation
    """

    # Filtere nur echte Mitglieder (mit Rolle)
    real_members = [m for m in committee.members if m.rolle in (Rolle.OBMANN, Rolle.OBMANN_STELLVERTRETER, Rolle.MITGLIED)]

    results: list[SlotEvaluation] = []

    # Für jede Woche
    for week in range(1, weeks + 1):
        # Für jeden Wochentag
        for weekday in WEEKDAYS:
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
                chair_present = chair and chair.person_id in present_ids
                deputy_present = deputy and deputy.person_id in present_ids

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
                    full_attendance=len(missing) == 0,
                )
                results.append(eval_result)

    # Sortiere nach Qualität
    return sort_evaluations(results)


def sort_evaluations(results: list[SlotEvaluation]) -> list[SlotEvaluation]:
    """Sortiere nach Priority: fullAttendance > chair > quorate > attendance."""
    return sorted(
        results,
        key=lambda e: (
            # Absteigend (höher ist besser)
            -int(e.full_attendance),
            -int(e.chair_present),
            -int(e.deputy_chair_present or False),
            -int(e.quorate),
            -e.attendance_count,
            -e.attendance_rate,
            # Aufsteigend (kleiner ist besser)
            WEEKDAY_SCORE[e.weekday],
            TIME_SCORE.get(e.start_time, 99),
        ),
    )


# ═══════════════════════════════════════════════════════════════════════════
# GLOBALES SCHEDULING - Konflikt-Vermeidung
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class GlobalSchedule:
    """Globale Planung mit Konflikt-Erkennung."""
    assigned: dict[int, SlotEvaluation]  # committee_id -> assigned SlotEvaluation
    conflicts: list[str] = field(default_factory=list)


def global_schedule_committees(
    all_evaluations: dict[int, list[SlotEvaluation]],
) -> GlobalSchedule:
    """Globale Planung mit Week-Load-Balancing.

    Algorithmus:
    1. Sortiere Ausschüsse nach Constraint-Komplexität (weniger Optionen first)
    2. Für jeden Ausschuss: Wähle beste verfügbare Option
       - PRIORITÄT: Woche mit weniger Ausschüssen (Load-Balance)
       - Keine Konflikte (week, weekday, start_time)
    3. Markiere Slot als belegt
    """
    assigned: dict[int, SlotEvaluation] = {}
    occupied: set[tuple[int, Wochentag, str]] = set()  # (week, weekday, start_time)
    week_counts = {}  # week -> count
    conflicts = []

    # Sortiere Ausschüsse nach Anzahl verfügbarer Optionen (ascending = constraints first)
    sorted_committees = sorted(
        all_evaluations.items(),
        key=lambda x: len(x[1]),
    )

    for committee_id, evaluations in sorted_committees:
        # Sortiere Evaluationen nach: Week-Load (ascending), dann Quality
        # Das bevorzugt leere Wochen vor vollen
        sorted_evals = sorted(
            evaluations,
            key=lambda e: (
                week_counts.get(e.week, 0),  # Woche mit weniger Ausschüssen first
                -int(e.full_attendance),  # Dann beste Quality
                -int(e.chair_present),
                -int(e.quorate),
            ),
        )

        # Finde erste nicht-konfliktfreie Option
        assigned_slot = None
        for evaluation in sorted_evals:
            slot_key = (evaluation.week, evaluation.weekday, evaluation.start_time)
            if slot_key not in occupied:
                assigned_slot = evaluation
                occupied.add(slot_key)
                week_counts[evaluation.week] = week_counts.get(evaluation.week, 0) + 1
                break

        if assigned_slot:
            assigned[committee_id] = assigned_slot
        else:
            conflicts.append(f"Ausschuss {committee_id}: Kein konfliktfreier Slot")

    return GlobalSchedule(assigned=assigned, conflicts=conflicts)


# ═══════════════════════════════════════════════════════════════════════════
# API (für calculation_service)
# ═══════════════════════════════════════════════════════════════════════════

def calculate_committee_dates(
    committees: list[CommitteeInput],
    weeks: int = 2,
    max_alternatives: int = 10,
    start_date: date | None = None,
) -> dict[int, list[SlotEvaluation]]:
    """Berechne beste Termine für alle Ausschüsse.

    Args:
        committees: Liste von CommitteeInput
        weeks: Anzahl der Planungswochen
        max_alternatives: Max. Anzahl Vorschläge pro Ausschuss
        start_date: Montag der ersten Planungswoche (optional, für Abwesenheits-Checks)

    Returns:
        dict[committee_id] -> list[SlotEvaluation] (top N)
    """
    result = {}
    for committee in committees:
        evaluations = evaluate_committee_slots(committee, weeks, start_date)
        # Gib Top N Termine pro Ausschuss
        result[committee.committee_id] = evaluations[:max_alternatives]
    return result
