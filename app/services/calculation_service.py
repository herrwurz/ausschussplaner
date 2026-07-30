"""Bindeglied zwischen DB und der Berechnungs-Engine.

Neue Architektur: Einfache Evaluierung statt komplexer globaler Scheduler.
"""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.enums import Rolle, TerminStatus, Wochentag
from app.models.models import Ausschuss, Mitgliedschaft, Person, Sitzungsregel, Sitzungsvorschlag
from app.schemas.schemas import (
    AusschussAnalyse,
    BerechnungRequest,
    BerechnungResponse,
    TerminVorschlagOut,
)
from app.services import scheduler as sched


def _minutes_to_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _load_fixed_slots(db: Session, ausschuss_ids: set[int]) -> list[sched.OccupiedSlot]:
    """Lade fixierte Sitzungsvorschläge als belegte Slots (mit Mitglieder-IDs)."""
    if not ausschuss_ids:
        return []
    vorschlaege = (
        db.query(Sitzungsvorschlag)
        .filter(Sitzungsvorschlag.ausschuss_id.in_(ausschuss_ids))
        .all()
    )
    if not vorschlaege:
        return []

    # Mitglieder je Ausschuss
    members_by_committee: dict[int, frozenset[int]] = {}
    for aid in {v.ausschuss_id for v in vorschlaege}:
        rows = db.query(Mitgliedschaft.person_id).filter(
            Mitgliedschaft.ausschuss_id == aid,
            Mitgliedschaft.rolle.in_([Rolle.OBMANN, Rolle.OBMANN_STELLVERTRETER, Rolle.MITGLIED]),
        ).all()
        members_by_committee[aid] = frozenset(r[0] for r in rows)

    blocked: list[sched.OccupiedSlot] = []
    for v in vorschlaege:
        name = v.ausschuss.name if v.ausschuss else f"Ausschuss {v.ausschuss_id}"
        blocked.append(sched.OccupiedSlot(
            week=v.woche,
            weekday=v.wochentag,
            start_time=_minutes_to_time(v.start_minute),
            end_time=_minutes_to_time(v.end_minute),
            person_ids=members_by_committee.get(v.ausschuss_id, frozenset()),
            committee_id=v.ausschuss_id,
            label=name,
        ))
    return blocked


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

        # Perioden-spezifische Verfügbarkeit überschreibt die Standardverfügbarkeit:
        # Gibt es Einträge für die Periode des Ausschusses, gelten NUR diese;
        # sonst Fallback auf Einträge ohne Periode (periode_id IS NULL).
        scope = ausschuss.periode_id
        relevante = [v for v in person.verfuegbarkeiten if v.periode_id == scope]
        if not relevante and scope is not None:
            relevante = [v for v in person.verfuegbarkeiten if v.periode_id is None]

        for verfug in relevante:
            if verfug.verfuegbar:
                # Konvertiere stunde float zu Zeit-String
                hour = int(verfug.stunde)  # z.B. 17
                minute = int((verfug.stunde - hour) * 60)  # z.B. 0 oder 30
                time_str = f"{hour:02d}:{minute:02d}"
                availability[verfug.wochentag].add(time_str)

        # Sammle Abwesenheits-Daten im Planungszeitraum
        absent_dates = frozenset()
        if start_date is not None and end_date is not None and db is not None:
            # Lade Abwesenheiten direkt aus DB für diesen Zeitraum
            abwesenheiten = db.query(Abwesenheit).filter(
                Abwesenheit.person_id == person.id,
                Abwesenheit.von <= end_date,
                Abwesenheit.bis >= start_date,
            ).all()
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

    from app.schemas.schemas import MitgliedDetail

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
        # Validierungsdaten:
        required_availability_hours=eval_result.required_availability_hours,
        anwesende_mitglieder=[MitgliedDetail(name=m.name, rolle=m.rolle) for m in eval_result.present_members],
        fehlende_mitglieder=[MitgliedDetail(name=m.name, rolle=m.rolle) for m in eval_result.missing_members],
    )


def run_calculation(db: Session, req: BerechnungRequest) -> BerechnungResponse:
    """Hauptfunktion: Berechne Vorschläge für alle Ausschüsse."""

    regel = _load_regel(db)
    weeks = req.planungswochen or regel.planungswochen
    freitag_modus = req.freitag_modus or regel.freitag_modus

    # F1: Die gesamte Datumsberechnung (Woche/Wochentag -> Datum) setzt voraus,
    # dass start_date ein MONTAG ist. Nicht-Montage (inkl. Default "heute")
    # werden auf den NÄCHSTEN Montag normalisiert, sonst passen die
    # ausgegebenen Daten nicht zu den Wochentags-Labels und Abwesenheiten
    # werden gegen falsche Kalendertage geprüft.
    start_date = req.start_datum or date.today()
    if start_date.weekday() != 0:
        start_date += timedelta(days=7 - start_date.weekday())

    # Lade Ausschüsse mit eager-loaded Verfügbarkeiten
    stmt = (
        select(Ausschuss)
        .options(
            selectinload(Ausschuss.mitgliedschaften)
            .selectinload(Mitgliedschaft.person)
            .selectinload(Person.verfuegbarkeiten),
        )
        .where(Ausschuss.aktiv.is_(True))
    )
    # Abwesenheiten werden lazy-loaded in _load_committee_input()
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
        evaluations = sched.evaluate_committee_slots(
            committee_input,
            weeks=weeks,
            start_date=start_date,
            freitag_modus=freitag_modus,
            fruehester_start=req.fruehester_start,
        )
        filtered = [e for e in evaluations if e.quote >= min_quote]
        all_evaluations_by_committee[ausschuss.id] = filtered

    # STEP 2: Global scheduling - Fixierte Termine + Tageslimit + Mitgliederkonflikte
    max_pro_tag = req.max_ausschuesse_pro_tag or regel.max_ausschuesse_pro_tag
    all_active_ids = set(
        db.scalars(select(Ausschuss.id).where(Ausschuss.aktiv.is_(True))).all()
    )
    # Fixierte Termine aller aktiven Ausschüsse (nicht nur der berechneten),
    # damit Personenkonflikte mit bereits fixierten anderen Gremien erkannt werden
    blocked = _load_fixed_slots(db, all_active_ids)
    global_schedule = sched.global_schedule_committees(
        all_evaluations_by_committee,
        blocked=blocked,
        max_ausschuesse_pro_tag=max_pro_tag,
        member_aware=True,
    )
    # STEP 3: Formatiere Ergebnisse
    analysen: list[AusschussAnalyse] = []

    for ausschuss in ausschuesse:
        evaluations = all_evaluations_by_committee.get(ausschuss.id, [])
        if not evaluations:
            # Ausschuss NICHT stillschweigend weglassen, sondern mit Hinweis ausweisen
            analysen.append(AusschussAnalyse(
                ausschuss_id=ausschuss.id,
                ausschuss_name=ausschuss.name,
                ausschuss_typ=ausschuss.typ,
                empfehlung_text=(
                    f"Kein Termin mit mind. {min_quote}% Verfügbarkeit gefunden. "
                    "Mindestquote senken oder Verfügbarkeiten prüfen."
                ),
            ))
            continue

        # Filtere nach Statusklasse (Spez §7 b–c)
        top_termine = [e for e in evaluations if e.full_attendance]
        besch_termine = [e for e in evaluations if e.quorate and not e.full_attendance]
        alt_termine = [e for e in evaluations if e.status == TerminStatus.ALTERNATIV]

        # Global assigned slot (conflict-free from backtracking)
        assigned = global_schedule.assigned.get(ausschuss.id)

        # Konvertiere zu TerminVorschlagOut
        top_vorschlaege = [_evaluation_to_termin(e, start_date, e.week) for e in top_termine[:max_alt]]
        besch_vorschlaege = [_evaluation_to_termin(e, start_date, e.week) for e in besch_termine[:max_alt]]
        alt_vorschlaege = [_evaluation_to_termin(e, start_date, e.week) for e in alt_termine[:max_alt]]

        # Beste Termine: ZUERST der assigned (conflict-free), dann TOP, dann Beschlussfähige
        beste = []
        if assigned:
            # Der assigned Termin ist IMMER der TOP (erste Option für Kalender)
            assigned_termin = _evaluation_to_termin(assigned, start_date, assigned.week)
            beste.append(assigned_termin)

        # Füge weitere TOP-Termine hinzu (sortiert nach Woche)
        for termin in sorted(top_vorschlaege, key=lambda t: (t.woche, t.start)):
            if len(beste) >= max_alt:
                break
            if (
                assigned
                and termin.woche == assigned_termin.woche
                and termin.wochentag == assigned_termin.wochentag
                and termin.start == assigned_termin.start
            ):
                continue  # Skip wenn schon added (gleicher Tag + gleiche Zeit)
            beste.append(termin)

        # Füge beschlussfähige Termine hinzu
        for termin in sorted(besch_vorschlaege, key=lambda t: (t.woche, t.start)):
            if len(beste) >= max_alt:
                break
            beste.append(termin)

        # Fülle Mitglieder-Liste
        from app.schemas.schemas import MitgliedOut
        mitglieder_list = [
            MitgliedOut(person_id=m.person_id, rolle=m.rolle, name=m.person.name)
            for m in ausschuss.mitgliedschaften
            if m.rolle in (Rolle.OBMANN, Rolle.OBMANN_STELLVERTRETER, Rolle.MITGLIED) and m.person.aktiv
        ]

        analyse = AusschussAnalyse(
            ausschuss_id=ausschuss.id,
            ausschuss_name=ausschuss.name,
            ausschuss_typ=ausschuss.typ,
            mitglieder=mitglieder_list,
            top_termine=top_vorschlaege,
            beschlussfaehig=besch_vorschlaege,
            alternativen=alt_vorschlaege,
            beste_je_tag=beste,
        )
        analysen.append(analyse)

    return BerechnungResponse(
        analysen=analysen,
        start_datum=start_date,
        planungswochen=weeks,
        zusammenfassung={
            "konflikte": global_schedule.conflicts,
            "zugewiesen": len(global_schedule.assigned),
            "ausschuesse": len(ausschuesse),
        },
    )


def save_calculation_results(db: Session, response: BerechnungResponse) -> int:
    """Stub: Speichert Ergebnisse. Momentan nicht implementiert."""
    return 0
