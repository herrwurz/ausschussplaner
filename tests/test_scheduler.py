"""Tests der reinen Berechnungs-Engine (aktuelle slot-basierte API).

Fachliche Festlegungen (2026-07):
- Randslots 07:00–08:30 und 19:00–20:30 sind gültige Sitzungszeiten; das
  Häkchen "07:00" bzw. "19:00" deckt den gesamten Block ab.
- Quorum STANDARD: Obmann anwesend + mind. 50% der Mitglieder
  (quorum_override ersetzt die 50%-Regel, nicht die Obmann-Pflicht).
- Priorität: top > beschlussfähig > Obmann+Stv. > nur Obmann;
  Freitag je eine Stufe schlechter. freitag_modus="nein" schließt Freitag aus.
"""
from __future__ import annotations

from datetime import date

from app.models.enums import AusschussTyp, Rolle, TerminStatus, Wochentag
from app.services.scheduler import (
    TIME_SLOTS,
    CommitteeInput,
    MemberInput,
    OccupiedSlot,
    SlotEvaluation,
    evaluate_committee_slots,
    global_schedule_committees,
    is_person_available_for_slot,
    is_quorate,
    priority_key,
    status_rank,
)

SLOT_BY_START = {s.start_time: s for s in TIME_SLOTS}

MONDAY = date(2026, 7, 6)  # Montag W1


def member(pid, rolle=Rolle.MITGLIED, avail=None, absent=frozenset(), name=None):
    return MemberInput(
        person_id=pid,
        name=name or f"P{pid}",
        rolle=rolle,
        availability=avail or {},
        absent_dates=frozenset(absent),
    )


def committee(members, typ=AusschussTyp.STANDARD, quorum_override=None):
    return CommitteeInput(1, "Test", typ, members, quorum_override)


# ── Slot-Abdeckung ────────────────────────────────────────────────────────────

def test_slot_requires_all_hours():
    """17:00–18:30 verlangt die Stunden 17 UND 18."""
    slot = SLOT_BY_START["17:00"]
    m_full = member(1, avail={Wochentag.MO: {"17:00", "18:00"}})
    m_partial = member(2, avail={Wochentag.MO: {"18:00"}})
    assert is_person_available_for_slot(m_full, Wochentag.MO, slot) is True
    assert is_person_available_for_slot(m_partial, Wochentag.MO, slot) is False


def test_edge_slots_exist_and_cover_full_block():
    """07:00–08:30 und 19:00–20:30 sind gültige Slots; das jeweilige
    Häkchen deckt laut fachlicher Festlegung den ganzen Block ab."""
    early = SLOT_BY_START["07:00"]
    late = SLOT_BY_START["19:00"]
    assert early.end_time == "08:30"
    assert late.end_time == "20:30"
    m = member(1, avail={Wochentag.MO: {"07:00", "19:00"}})
    assert is_person_available_for_slot(m, Wochentag.MO, early) is True
    assert is_person_available_for_slot(m, Wochentag.MO, late) is True


def test_half_hour_start_requires_both_full_hours():
    """18:30-Start: 18:00=Nein, 19:00=Ja -> nicht anwesend."""
    slot = SLOT_BY_START["18:30"]
    m = member(1, avail={Wochentag.MO: {"19:00"}})
    assert is_person_available_for_slot(m, Wochentag.MO, slot) is False


# ── Quorum ────────────────────────────────────────────────────────────────────

def test_obmann_absent_means_not_quorate():
    members = [
        member(1, Rolle.OBMANN),
        member(2), member(3), member(4),
    ]
    c = committee(members)
    assert is_quorate(c, members, present_ids={2, 3, 4}) is False


def test_standard_quorum_is_chair_plus_half():
    members = [member(1, Rolle.OBMANN), member(2), member(3), member(4)]
    c = committee(members)
    assert is_quorate(c, members, present_ids={1}) is False        # 1 < 2
    assert is_quorate(c, members, present_ids={1, 2}) is True      # 2 >= 2


def test_quorum_override_replaces_half_rule():
    members = [member(1, Rolle.OBMANN), member(2), member(3), member(4)]
    c = committee(members, quorum_override=4)
    assert is_quorate(c, members, present_ids={1, 2}) is False     # 2 < 4
    assert is_quorate(c, members, present_ids={1, 2, 3, 4}) is True


def test_duplicate_member_deduplicated():
    """Dieselbe person_id darf nicht doppelt zählen."""
    avail = {Wochentag.MO: {"17:00", "18:00"}}
    members = [
        member(1, Rolle.OBMANN, avail),
        member(1, Rolle.MITGLIED, avail, name="Duplikat"),
        member(2, Rolle.MITGLIED, avail),
    ]
    res = evaluate_committee_slots(committee(members), weeks=1)
    assert all(e.total_members == 2 for e in res)


# ── Status & Priorität ────────────────────────────────────────────────────────

def test_empty_committee_is_not_top():
    """Ausschuss ohne Mitglieder darf keinen 100%-Termin erzeugen."""
    res = evaluate_committee_slots(committee([]), weeks=1)
    assert res
    assert all(e.full_attendance is False for e in res)
    assert all(e.status == TerminStatus.NICHT_BESCHLUSSFAEHIG for e in res)


def test_full_attendance_is_top():
    avail = {Wochentag.DI: {"16:00", "17:00"}}
    members = [member(1, Rolle.OBMANN, avail), member(2, avail=avail)]
    res = evaluate_committee_slots(committee(members), weeks=1)
    tops = [e for e in res if e.status == TerminStatus.TOP]
    assert tops and all(e.quote == 100 for e in tops)


def test_chair_and_deputy_under_quorum_is_alternativ():
    avail = {Wochentag.MO: {"17:00", "18:00"}}
    members = [
        member(1, Rolle.OBMANN, avail),
        member(2, Rolle.OBMANN_STELLVERTRETER, avail),
        member(3), member(4), member(5), member(6),  # nie verfügbar
    ]
    res = evaluate_committee_slots(committee(members), weeks=1)
    mo_17 = [e for e in res if e.weekday == Wochentag.MO and e.start_time == "17:00"]
    assert mo_17 and mo_17[0].status == TerminStatus.ALTERNATIV


def test_quorate_ranks_above_chair_plus_deputy():
    """Beschlussfähig (ohne Stv.) muss besser sein als Obmann+Stv. unter Quorum."""
    avail_mo = {Wochentag.MO: {"17:00", "18:00"}}
    avail_di = {Wochentag.DI: {"17:00", "18:00"}}
    members = [
        member(1, Rolle.OBMANN, {**avail_mo, **avail_di}),
        member(2, Rolle.OBMANN_STELLVERTRETER, avail_mo),   # nur Mo
        member(3, avail=avail_di), member(4, avail=avail_di),  # nur Di
        member(5), member(6),
    ]
    res = evaluate_committee_slots(committee(members), weeks=1)
    best = res[0]
    # Di: Obmann + 2 Mitglieder = 3 von 6 -> beschlussfähig (Rang 2)
    # Mo: Obmann + Stv. = 2 von 6 -> ALTERNATIV (Rang 4)
    assert best.weekday == Wochentag.DI
    assert best.status == TerminStatus.BESCHLUSSFAEHIG


def test_friday_is_one_rank_worse():
    avail = {Wochentag.FR: {"17:00", "18:00"}, Wochentag.DI: {"17:00", "18:00"}}
    members = [member(1, Rolle.OBMANN, avail), member(2, avail=avail)]
    res = evaluate_committee_slots(committee(members), weeks=1)
    fr = next(e for e in res if e.weekday == Wochentag.FR and e.full_attendance)
    di = next(e for e in res if e.weekday == Wochentag.DI and e.full_attendance)
    assert status_rank(di) == 0
    assert status_rank(fr) == 1
    assert priority_key(di) < priority_key(fr)
    assert res[0].weekday == Wochentag.DI


def test_freitag_modus_nein_excludes_friday():
    avail = {Wochentag.FR: {"17:00", "18:00"}}
    members = [member(1, Rolle.OBMANN, avail)]
    res = evaluate_committee_slots(committee(members), weeks=1, freitag_modus="nein")
    assert all(e.weekday != Wochentag.FR for e in res)


# ── Abwesenheiten & Datum ─────────────────────────────────────────────────────

def test_absence_blocks_otherwise_available_slot():
    slot = SLOT_BY_START["16:00"]
    m = member(1, avail={Wochentag.MO: {"16:00", "17:00"}}, absent=[MONDAY])
    assert is_person_available_for_slot(m, Wochentag.MO, slot, meeting_date=MONDAY) is False
    assert is_person_available_for_slot(m, Wochentag.MO, slot, meeting_date=None) is True


def test_absence_applies_to_correct_week():
    """Abwesenheit am Di W1 blockiert nicht Di W2."""
    tuesday_w1 = date(2026, 7, 7)
    avail = {Wochentag.DI: {"17:00", "18:00"}}
    members = [member(1, Rolle.OBMANN, avail, absent=[tuesday_w1])]
    res = evaluate_committee_slots(committee(members), weeks=2, start_date=MONDAY)
    di_w1 = [e for e in res if e.weekday == Wochentag.DI and e.week == 1]
    di_w2 = [e for e in res if e.weekday == Wochentag.DI and e.week == 2]
    assert all(e.attendance_count == 0 for e in di_w1)
    assert any(e.attendance_count == 1 for e in di_w2)


# ── Globaler Scheduler ────────────────────────────────────────────────────────

def _make_eval(cid, week, weekday, start, end, person_ids=None):
    pids = list(person_ids) if person_ids is not None else []
    present = [
        MemberInput(pid, f"P{pid}", Rolle.MITGLIED, {}, frozenset())
        for pid in pids
    ]
    return SlotEvaluation(
        committee_id=cid, committee_name=f"C{cid}", week=week, weekday=weekday,
        start_time=start, end_time=end, required_availability_hours=[],
        present_members=present, missing_members=[], attendance_count=max(len(pids), 1),
        total_members=max(len(pids), 1), attendance_rate=1.0, chair_present=True,
        deputy_chair_present=False, quorate=True, full_attendance=True,
    )


def test_global_schedule_avoids_overlap():
    # Ohne person_ids → Hard-Block bei Zeitüberlappung (leere Mengen)
    opts1 = [_make_eval(1, 1, Wochentag.MO, "17:00", "18:30"),
             _make_eval(1, 2, Wochentag.MO, "17:00", "18:30")]
    opts2 = [_make_eval(2, 1, Wochentag.MO, "17:00", "18:30"),
             _make_eval(2, 2, Wochentag.MO, "17:00", "18:30")]
    schedule = global_schedule_committees({1: opts1, 2: opts2})
    a1, a2 = schedule.assigned[1], schedule.assigned[2]
    assert (a1.week, a1.weekday) != (a2.week, a2.weekday) or a1.start_time != a2.start_time


def test_global_schedule_allows_parallel_without_shared_members():
    """Ohne gemeinsame Personen dürfen parallele Termine stattfinden."""
    opts1 = [_make_eval(1, 1, Wochentag.MO, "17:00", "18:30", person_ids=[1, 2])]
    opts2 = [_make_eval(2, 1, Wochentag.MO, "17:00", "18:30", person_ids=[3, 4])]
    schedule = global_schedule_committees({1: opts1, 2: opts2}, member_aware=True)
    assert schedule.assigned[1].week == schedule.assigned[2].week
    assert schedule.assigned[1].start_time == schedule.assigned[2].start_time


def test_global_schedule_blocks_shared_members():
    opts1 = [_make_eval(1, 1, Wochentag.MO, "17:00", "18:30", person_ids=[1, 2]),
             _make_eval(1, 1, Wochentag.DI, "17:00", "18:30", person_ids=[1, 2])]
    opts2 = [_make_eval(2, 1, Wochentag.MO, "17:00", "18:30", person_ids=[2, 3])]
    schedule = global_schedule_committees({1: opts1, 2: opts2}, member_aware=True)
    a1, a2 = schedule.assigned[1], schedule.assigned[2]
    # Person 2 in beiden → nicht parallel Mo 17:00
    assert not (
        a1.week == a2.week and a1.weekday == a2.weekday and a1.start_time == a2.start_time
    )


def test_global_schedule_respects_fixed_and_max_per_day():
    blocked = [OccupiedSlot(
        week=1, weekday=Wochentag.MO, start_time="17:00", end_time="18:30",
        person_ids=frozenset({10}), committee_id=99, label="Fix",
    )]
    opts = [
        _make_eval(1, 1, Wochentag.MO, "17:00", "18:30", person_ids=[10, 11]),
        _make_eval(1, 1, Wochentag.DI, "17:00", "18:30", person_ids=[10, 11]),
    ]
    schedule = global_schedule_committees(
        {1: opts}, blocked=blocked, max_ausschuesse_pro_tag=2, member_aware=True,
    )
    assert schedule.assigned[1].weekday == Wochentag.DI
    assert not any("Fixiert" in c for c in schedule.conflicts)

    # Tageslimit: Mo schon 1x belegt → max=1 erzwingt anderen Tag
    opts_a = [_make_eval(1, 1, Wochentag.MO, "16:00", "17:30", person_ids=[1])]
    opts_b = [
        _make_eval(2, 1, Wochentag.MO, "18:00", "19:30", person_ids=[2]),
        _make_eval(2, 1, Wochentag.DI, "18:00", "19:30", person_ids=[2]),
    ]
    schedule2 = global_schedule_committees(
        {1: opts_a, 2: opts_b}, max_ausschuesse_pro_tag=1, member_aware=True,
    )
    assert schedule2.assigned[2].weekday == Wochentag.DI


def test_global_schedule_empty_membership_does_not_hard_block():
    """Fixierte Termine ohne Mitglieder blockieren nur bei echter Personenüberschneidung."""
    blocked = [OccupiedSlot(
        week=1, weekday=Wochentag.MO, start_time="17:00", end_time="18:30",
        person_ids=frozenset(), committee_id=99, label="Leer",
    )]
    opts1 = [_make_eval(1, 1, Wochentag.MO, "17:00", "18:30", person_ids=[1, 2])]
    opts2 = [_make_eval(2, 1, Wochentag.MO, "17:00", "18:30", person_ids=[3, 4])]
    schedule = global_schedule_committees({1: opts1, 2: opts2}, blocked=blocked, member_aware=True)
    assert schedule.assigned[1].weekday == schedule.assigned[2].weekday == Wochentag.MO
    assert schedule.assigned[1].start_time == schedule.assigned[2].start_time


def test_global_schedule_skips_committee_without_options():
    """Leere Optionsliste darf weder crashen noch andere Zuweisungen verhindern."""
    opts = [_make_eval(2, 1, Wochentag.MO, "17:00", "18:30")]
    schedule = global_schedule_committees({1: [], 2: opts})
    assert 1 not in schedule.assigned
    assert 2 in schedule.assigned
    assert any("1" in c for c in schedule.conflicts)
