"""Tests der reinen Berechnungs-Engine (Masterprompt-Regeln)."""
from __future__ import annotations

from datetime import date

from app.models.enums import AusschussTyp, Rolle, TerminStatus, Wochentag
from app.services.scheduler import (
    CommitteeInput,
    MemberInput,
    allowed_starts,
    calculate_committee,
    is_present,
    required_hours,
)


def test_required_hours_masterprompt_examples():
    assert required_hours(7 * 60, 90) == [7, 8]
    assert required_hours(16 * 60, 90) == [16, 17]
    assert required_hours(17 * 60, 90) == [17, 18]
    assert required_hours(18 * 60 + 30, 90) == [18, 19]


def test_person_partial_availability_not_present():
    """18:00=Nein, 19:00=Ja -> nicht anwesend bei 18:30-Start."""
    m = MemberInput(1, "X", Rolle.MITGLIED, {Wochentag.MO: {19}})
    assert is_present(m, Wochentag.MO, 18 * 60 + 30, 90) is False


def test_person_full_block_present():
    m = MemberInput(1, "X", Rolle.MITGLIED, {Wochentag.MO: {18, 19}})
    assert is_present(m, Wochentag.MO, 18 * 60 + 30, 90) is True


def test_allowed_starts_includes_half_hours():
    starts = allowed_starts()
    assert 16 * 60 in starts
    assert 16 * 60 + 30 in starts


def test_only_real_members_counted():
    """Mitglieder ohne gültige Rolle dürfen nicht gezählt werden.

    (Hier implizit: nur übergebene MemberInputs zählen — die DB-Schicht
    filtert '-'/leer bereits heraus.)
    """
    members = [
        MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.MO: {16, 17}}),
        MemberInput(2, "M", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
    ]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members),
        weeks=1,
    )
    assert len(res.members) == 2


def test_obmann_absent_means_not_quorate():
    """Ohne Obmann nie beschlussfähig, egal wie viele Mitglieder."""
    members = [
        MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.MO: set()}),  # nie da
        MemberInput(2, "A", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
        MemberInput(3, "B", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
        MemberInput(4, "C", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
    ]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members), weeks=1
    )
    mo_slots = [s for s in res.all_slots if s.day == Wochentag.MO]
    assert all(s.status == TerminStatus.NICHT_BESCHLUSSFAEHIG for s in mo_slots)


def test_full_attendance_is_top():
    members = [
        MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.DI: {16, 17}}),
        MemberInput(2, "A", Rolle.MITGLIED, {Wochentag.DI: {16, 17}}),
        MemberInput(3, "B", Rolle.MITGLIED, {Wochentag.DI: {16, 17}}),
    ]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members), weeks=1
    )
    tops = [s for s in res.all_slots if s.status == TerminStatus.TOP and s.day == Wochentag.DI]
    assert len(tops) > 0
    assert all(s.quote == 100 for s in tops)


def test_duplicate_member_deduplicated():
    members = [
        MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.MO: {16, 17}}),
        MemberInput(1, "Ob dup", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
    ]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members), weeks=1
    )
    assert len(res.members) == 1


# ── Abwesenheits-Tests ────────────────────────────────────────────────────────

def test_absence_blocks_otherwise_available_slot():
    """Person mit Abwesenheit am Montag wird nicht als anwesend gezählt."""
    monday = date(2026, 6, 8)  # Montag
    m = MemberInput(
        1, "X", Rolle.MITGLIED,
        {Wochentag.MO: {16, 17}},
        absent_dates=frozenset([monday]),
    )
    assert is_present(m, Wochentag.MO, 16 * 60, 90, slot_date=monday) is False


def test_absence_on_other_day_does_not_block():
    """Abwesenheit am Montag blockiert nicht am Dienstag."""
    monday = date(2026, 6, 8)
    tuesday = date(2026, 6, 9)
    m = MemberInput(
        1, "X", Rolle.MITGLIED,
        {Wochentag.DI: {16, 17}},
        absent_dates=frozenset([monday]),
    )
    assert is_present(m, Wochentag.DI, 16 * 60, 90, slot_date=tuesday) is True


def test_absence_reduces_attendance_in_calculation():
    """Wenn der Obmann am ersten Montag der Planung abwesend ist, darf kein
    beschlussfähiger Termin an diesem Tag entstehen."""
    start = date(2026, 6, 8)  # Montag W1
    monday_w1 = date(2026, 6, 8)
    members = [
        MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.MO: {16, 17}},
                    absent_dates=frozenset([monday_w1])),
        MemberInput(2, "A", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
        MemberInput(3, "B", Rolle.MITGLIED, {Wochentag.MO: {16, 17}}),
    ]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members),
        weeks=1,
        start_date=start,
    )
    mo_w1 = [
        s for s in res.all_slots
        if s.day == Wochentag.MO and s.datum == monday_w1
    ]
    assert all(s.status == TerminStatus.NICHT_BESCHLUSSFAEHIG for s in mo_w1)


def test_slot_datum_set_when_start_date_given():
    """Slot.datum wird korrekt aus start_date + Woche + Tag berechnet."""
    start = date(2026, 6, 8)  # Montag
    members = [MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.DI: {16, 17}})]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members),
        weeks=2,
        start_date=start,
    )
    di_w2 = [s for s in res.all_slots if s.day == Wochentag.DI and s.week == 2]
    assert di_w2, "Keine Slots für Di W2 gefunden"
    expected = date(2026, 6, 16)  # start + 8 Tage
    assert all(s.datum == expected for s in di_w2)


def test_no_start_date_leaves_datum_none():
    """Ohne start_date bleibt Slot.datum None (Rückwärtskompatibilität)."""
    members = [MemberInput(1, "Ob", Rolle.OBMANN, {Wochentag.MO: {16, 17}})]
    res = calculate_committee(
        CommitteeInput(1, "C", AusschussTyp.POLY, members), weeks=1
    )
    assert all(s.datum is None for s in res.all_slots)
