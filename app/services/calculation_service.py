"""Bindeglied zwischen DB und der Berechnungs-Engine.

Neue Architektur: Einfache Evaluierung statt komplexer globaler Scheduler.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import AusschussTyp, Rolle, TerminStatus, Wochentag
from app.models.models import Ausschuss, Mitgliedschaft, Person, Sitzungsregel
from app.schemas.schemas import (
    AusschussAnalyse,
    BerechnungRequest,
    BerechnungResponse,
    TerminVorschlagOut,
)
from app.services import scheduler as sched


def _load_regel(db: Session) -> Sitzungsregel:
    """Lade oder erstelle Sitzungsregel (Singleton)."""
    regel = db.get(Sitzungsregel, 1)
    if regel is None:
        regel = Sitzungsregel(id=1)
        db.add(regel)
        db.commit()
        db.refresh(regel)
    return regel


def _load_committee_input(
    ausschuss: Ausschuss,
    start_date: date | None = None,
    weeks: int = 2,
    db: Session | None = None,
) -> sched.CommitteeInput:
    """Konvertiere ORM-Ausschuss zu scheduler.CommitteeInput.

    Args:
        ausschuss: ORM-Ausschuss
        start_date: Montag der ersten Planungswoche (optional, für Abwesenheits-Range)
        weeks: Anzahl der Planungswochen (für Abwesenheits-Range)
        db: DB-Session (optional, für Abwesenheits-Lookup falls nicht eager-loaded)

    Returns:
        CommitteeInput mit gefüllter Verfügbarkeit und Abwesenheiten
    """
    from app.models.models import Abwesenheit

    # Filtere nur aktive Mitglieder mit echter Rolle
    real_members = [
        m for m in ausschuss.mitgliedschaften
        if m.rolle in (Rolle.OBMANN, Rolle.OBMANN_STELLVERTRETER, Rolle.MITGLIED)
        and m.person.aktiv
    ]

    # Berechne Planungszeitraum-Grenzen für Abwesenheits-Range
    end_date = None
    if start_date is not None:
        end_date = start_date + timedelta(days=weeks * 7 - 1)

    # Baue MemberInput für jeden Mitglied
    member_inputs: list[sched.MemberInput] = []
    for mitglied in real_members:
        person = mitglied.person

        # Verfügbarkeit: dict[Wochentag] -> set[str] von "HH:MM"
        availability: dict[Wochentag, set[str]] = {
            day: set() for day in sched.WEEKDAYS
        }

        for verfug in person.verfuegbarkeiten:
            if verfug.verfuegbar:
                # Konvertiere stunde float zu Zeit-String
                hour = int(verfug.stunde)  # z.B. 17
                minute = int((verfug.stunde - hour) * 60)  # z.B. 0 oder 30
                time_str = f"{hour:02d}:{minute:02d}"
                availability[verfug.wochentag].add(time_str)

        # Sammle Abwesenheits-Daten im Planungszeitraum
        absent_dates = frozenset()
        if start_date is not None and end_date is not None:
            # Lade Abwesenheiten aus Eager-Loaded-Rel. oder DB
            abwesenheiten = person.abwesenheiten
            for ab in abwesenheiten:
                # Finde alle Daten im Bereich [von, bis] die im Planungszeitraum liegen
                ab_start = max(ab.von, start_date)
                ab_end = min(ab.bis, end_date)
                if ab_start <= ab_end:
                    # Alle Tage im Bereich
                    current_day = ab_start
                    dates = []
                    while current_day <= ab_end:
                        dates.append(current_day)
                        current_day += timedelta(days=1)
                    absent_dates = absent_dates.union(dates)

        member_inputs.append(
            sched.MemberInput(
                person_id=person.id,
                name=person.name,
                rolle=mitglied.rolle,
                availability=availability,
                absent_dates=absent_dates,
            )
        )

    return sched.CommitteeInput(
        committee_id=ausschuss.id,
        name=ausschuss.name,
        typ=ausschuss.typ,
        members=member_inputs,
        quorum_override=None,
    )


def _evaluation_to_termin(
    eval_result: sched.SlotEvaluation,
    start_date: date,
    week: int,
) -> TerminVorschlagOut:
    """Konvertiere SlotEvaluation zu TerminVorschlagOut."""

    # Berechne Datum basierend auf Wochentag
    weekday_offset = {
        Wochentag.MO: 0,
        Wochentag.DI: 1,
        Wochentag.MI: 2,
        Wochentag.DO: 3,
        Wochentag.FR: 4,
    }
    days_offset = (week - 1) * 7 + weekday_offset[eval_result.weekday]
    datum = start_date + timedelta(days=days_offset)

    return TerminVorschlagOut(
        woche=week,
        wochentag=eval_result.weekday,
        start=eval_result.start_time,
        ende=eval_result.end_time,
        datum=datum,
        ausschuss_id=eval_result.committee_id,
        ausschuss_name=eval_result.committee_name,
        obmann_da=eval_result.chair_present,
        stv_da=eval_result.deputy_chair_present,
        anwesend=eval_result.attendance_count,
        mitglieder=eval_result.total_members,
        quote=eval_result.quote,
        status=eval_result.status,
        empfehlung=eval_result.status.name,
        fehlende=[m.name for m in eval_result.missing_members],
    )


def run_calculation(db: Session, req: BerechnungRequest) -> BerechnungResponse:
    """Hauptfunktion: Berechne Vorschläge für alle Ausschüsse."""

    regel = _load_regel(db)
    weeks = req.planungswochen or regel.planungswochen
    start_date = req.start_datum or date.today()

    # Lade Ausschüsse mit eager-loaded Verfügbarkeiten und Abwesenheiten
    stmt = (
        select(Ausschuss)
        .options(
            selectinload(Ausschuss.mitgliedschaften)
            .selectinload(Mitgliedschaft.person)
            .selectinload(Person.verfuegbarkeiten),
            selectinload(Ausschuss.mitgliedschaften)
            .selectinload(Mitgliedschaft.person)
            .selectinload(Person.abwesenheiten),
        )
        .where(Ausschuss.aktiv.is_(True))
    )
    if req.ausschuss_ids:
        stmt = stmt.where(Ausschuss.id.in_(req.ausschuss_ids))
    if req.periode_id:
        stmt = stmt.where(Ausschuss.periode_id == req.periode_id)

    ausschuesse = db.scalars(stmt).unique().all()

    # STEP 1: Evaluiere ALLE Ausschüsse einzeln
    min_quote = req.min_verfuegbarkeit or 0
    max_alt = req.max_alternativen or 10
    all_evaluations_by_committee: dict[int, list[sched.SlotEvaluation]] = {}

    for ausschuss in ausschuesse:
        committee_input = _load_committee_input(ausschuss, start_date=start_date, weeks=weeks, db=db)
        evaluations = sched.evaluate_committee_slots(committee_input, weeks=weeks, start_date=start_date)
        filtered = [e for e in evaluations if e.quote >= min_quote]
        all_evaluations_by_committee[ausschuss.id] = filtered

    # STEP 2: Global scheduling - Vermeidung von Konflikten
    global_schedule = sched.global_schedule_committees(all_evaluations_by_committee)

    # STEP 3: Formatiere Ergebnisse
    analysen: list[AusschussAnalyse] = []

    for ausschuss in ausschuesse:
        evaluations = all_evaluations_by_committee.get(ausschuss.id, [])
        if not evaluations:
            continue

        # Filtere nach Typ
        top_termine = [e for e in evaluations if e.full_attendance]
        besch_termine = [e for e in evaluations if e.quorate and not e.full_attendance]

        # Global assigned slot
        assigned = global_schedule.assigned.get(ausschuss.id)

        # Konvertiere zu TerminVorschlagOut
        top_vorschlaege = [_evaluation_to_termin(e, start_date, e.week) for e in top_termine[:max_alt]]
        besch_vorschlaege = [_evaluation_to_termin(e, start_date, e.week) for e in besch_termine[:max_alt]]

        # Beste Termin: entweder global assigned oder beste Option
        beste = []
        if assigned:
            beste = [_evaluation_to_termin(assigned, start_date, assigned.week)]
        elif top_vorschlaege:
            beste = top_vorschlaege[:1]
        elif besch_vorschlaege:
            beste = besch_vorschlaege[:1]

        analyse = AusschussAnalyse(
            ausschuss_id=ausschuss.id,
            ausschuss_name=ausschuss.name,
            ausschuss_typ=ausschuss.typ,
            top_termine=top_vorschlaege,
            beschlussfaehig=besch_vorschlaege,
            alternativen=[],
            beste_je_tag=beste,
        )
        analysen.append(analyse)

    return BerechnungResponse(
        analysen=analysen,
        start_datum=start_date,
        planungswochen=weeks,
    )


def save_calculation_results(db: Session, response: BerechnungResponse) -> int:
    """Stub: Speichert Ergebnisse. Momentan nicht implementiert."""
    return 0
