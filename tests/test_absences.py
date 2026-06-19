"""Tests für Abwesenheits-Verwaltung und deren Integration in die Terminberechnung."""
from __future__ import annotations

from datetime import date, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import AbwesenheitsArt, AusschussTyp, Rolle, TerminStatus, Wochentag
from app.models.models import Abwesenheit, Ausschuss, Mitgliedschaft, Person, Verfuegbarkeit
from app.services.scheduler import (
    CommitteeInput,
    MemberInput,
    is_person_absent,
    is_person_available_for_slot,
    evaluate_committee_slots,
    TimeSlot,
)


@pytest.fixture
def setup_person_with_availability(db_session: Session) -> Person:
    """Erstelle Person mit Standard-Verfügbarkeit (Mo-Fr 16:00-19:00)."""
    person = Person(vorname="Test", nachname="Person", aktiv=True)
    db_session.add(person)
    db_session.flush()

    for weekday in [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]:
        for hour in [16, 17, 18, 19]:
            verfug = Verfuegbarkeit(
                person_id=person.id,
                wochentag=weekday,
                stunde=float(hour),
                verfuegbar=True,
            )
            db_session.add(verfug)

    db_session.commit()
    db_session.refresh(person)
    return person


def test_is_person_absent_returns_true_for_matching_date():
    """is_person_absent gibt True zurück, wenn Datum in absent_dates."""
    monday = date(2026, 6, 8)
    member = MemberInput(
        person_id=1,
        name="Test",
        rolle=Rolle.MITGLIED,
        availability={Wochentag.MO: {"16:00"}},
        absent_dates=frozenset([monday]),
    )
    assert is_person_absent(member, monday) is True


def test_is_person_absent_returns_false_for_non_matching_date():
    """is_person_absent gibt False zurück, wenn Datum nicht in absent_dates."""
    monday = date(2026, 6, 8)
    tuesday = date(2026, 6, 9)
    member = MemberInput(
        person_id=1,
        name="Test",
        rolle=Rolle.MITGLIED,
        availability={Wochentag.MO: {"16:00"}},
        absent_dates=frozenset([monday]),
    )
    assert is_person_absent(member, tuesday) is False


def test_is_person_absent_empty_frozenset():
    """is_person_absent gibt False zurück, wenn absent_dates leer."""
    monday = date(2026, 6, 8)
    member = MemberInput(
        person_id=1,
        name="Test",
        rolle=Rolle.MITGLIED,
        availability={Wochentag.MO: {"16:00"}},
        absent_dates=frozenset(),
    )
    assert is_person_absent(member, monday) is False


def test_is_person_available_for_slot_without_date():
    """Ohne meeting_date: is_person_available_for_slot nutzt nur Verfügbarkeit."""
    member = MemberInput(
        person_id=1,
        name="Test",
        rolle=Rolle.MITGLIED,
        availability={Wochentag.MO: {"16:00", "17:00"}},
        absent_dates=frozenset([date(2026, 6, 8)]),
    )
    slot = TimeSlot("16:00", "17:30", ["16:00"])
    # Ohne meeting_date wird Abwesenheit ignoriert
    result = is_person_available_for_slot(member, Wochentag.MO, slot)
    assert result is True


def test_is_person_available_for_slot_with_absence():
    """Mit meeting_date und Abwesenheit: Return False sofort."""
    monday = date(2026, 6, 8)
    member = MemberInput(
        person_id=1,
        name="Test",
        rolle=Rolle.MITGLIED,
        availability={Wochentag.MO: {"16:00", "17:00"}},
        absent_dates=frozenset([monday]),
    )
    slot = TimeSlot("16:00", "17:30", ["16:00"])
    result = is_person_available_for_slot(member, Wochentag.MO, slot, monday)
    assert result is False


def test_is_person_available_for_slot_no_absence_on_date():
    """Mit meeting_date ohne Abwesenheit: Prüfe normale Verfügbarkeit."""
    monday = date(2026, 6, 8)
    tuesday = date(2026, 6, 9)
    member = MemberInput(
        person_id=1,
        name="Test",
        rolle=Rolle.MITGLIED,
        availability={Wochentag.DI: {"16:00", "17:00"}},
        absent_dates=frozenset([monday]),
    )
    slot = TimeSlot("16:00", "17:30", ["16:00"])
    # Abwesenheit am Montag blockiert nicht Dienstag
    result = is_person_available_for_slot(member, Wochentag.DI, slot, tuesday)
    assert result is True


def test_absence_blocks_committee_slot_evaluation():
    """Wenn Obmann am Termin abwesend: Slot nicht beschlussfähig."""
    monday = date(2026, 6, 8)
    members = [
        MemberInput(
            person_id=1,
            name="Obmann",
            rolle=Rolle.OBMANN,
            availability={Wochentag.MO: {"16:00", "17:00"}},
            absent_dates=frozenset([monday]),
        ),
        MemberInput(
            person_id=2,
            name="Mitglied A",
            rolle=Rolle.MITGLIED,
            availability={Wochentag.MO: {"16:00", "17:00"}},
            absent_dates=frozenset(),
        ),
        MemberInput(
            person_id=3,
            name="Mitglied B",
            rolle=Rolle.MITGLIED,
            availability={Wochentag.MO: {"16:00", "17:00"}},
            absent_dates=frozenset(),
        ),
    ]
    committee = CommitteeInput(1, "TestComm", AusschussTyp.STANDARD, members)

    evaluations = evaluate_committee_slots(committee, weeks=1, start_date=monday)

    # Suche Montag-Slots in Woche 1
    mo_slots = [e for e in evaluations if e.weekday == Wochentag.MO and e.week == 1]
    assert len(mo_slots) > 0

    # Alle Montag-Slots sollten NICHT beschlussfähig sein (Obmann abwesend)
    for slot in mo_slots:
        assert slot.status in (TerminStatus.NICHT_BESCHLUSSFAEHIG, TerminStatus.OBMANN_DA)
        assert not slot.chair_present, f"Obmann sollte nicht anwesend sein, aber chair_present={slot.chair_present}"


def test_multiple_absences_reduce_attendance():
    """Mehrere Personen abwesend → weniger Anwesenheit."""
    start_date = date(2026, 6, 8)  # Montag
    monday_w1 = start_date
    tuesday_w1 = start_date + timedelta(days=1)

    members = [
        MemberInput(
            person_id=1,
            name="Ob",
            rolle=Rolle.OBMANN,
            availability={Wochentag.MO: {"16:00", "17:00", "18:00"}, Wochentag.DI: {"16:00", "17:00", "18:00"}},
            absent_dates=frozenset([monday_w1]),  # Montag abwesend
        ),
        MemberInput(
            person_id=2,
            name="A",
            rolle=Rolle.MITGLIED,
            availability={Wochentag.MO: {"16:00", "17:00", "18:00"}, Wochentag.DI: {"16:00", "17:00", "18:00"}},
            absent_dates=frozenset(),
        ),
        MemberInput(
            person_id=3,
            name="B",
            rolle=Rolle.MITGLIED,
            availability={Wochentag.MO: {"16:00", "17:00", "18:00"}, Wochentag.DI: {"16:00", "17:00", "18:00"}},
            absent_dates=frozenset([tuesday_w1]),  # Dienstag abwesend
        ),
    ]
    committee = CommitteeInput(1, "C", AusschussTyp.STANDARD, members)

    evals = evaluate_committee_slots(committee, weeks=1, start_date=start_date)

    # Mo Slots: nur 2 Mitglieder (A, B) anwesend, Obmann weg → nicht beschlussfähig
    mo_slots = [e for e in evals if e.weekday == Wochentag.MO and e.week == 1 and e.start_time == "16:00"]
    assert len(mo_slots) > 0, "Keine Mo-16:00-Slots gefunden"
    for slot in mo_slots:
        assert slot.attendance_count == 2, f"MO {slot.start_time}: erwartet 2, got {slot.attendance_count}"
        assert not slot.chair_present, f"Obmann sollte nicht anwesend sein"

    # Di Slots: nur 2 Mitglieder (Ob, A) anwesend, B weg → beschlussfähig (Ob+A)
    di_slots = [e for e in evals if e.weekday == Wochentag.DI and e.week == 1 and e.start_time == "16:00"]
    assert len(di_slots) > 0, "Keine Di-16:00-Slots gefunden"
    for slot in di_slots:
        assert slot.attendance_count == 2, f"DI {slot.start_time}: erwartet 2, got {slot.attendance_count}"
        assert slot.chair_present, f"Obmann sollte anwesend sein"


def test_absence_api_create_and_list(client, setup_person_with_availability: Person):
    """Test: Erstelle Abwesenheit via API, liste auf."""
    person_id = setup_person_with_availability.id
    von = date(2026, 7, 1)
    bis = date(2026, 7, 7)

    # POST /api/absences
    response = client.post(
        "/api/absences",
        json={
            "person_id": person_id,
            "von": von.isoformat(),
            "bis": bis.isoformat(),
            "art": "Urlaub",
            "bemerkung": "Sommerferien",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["person_id"] == person_id
    assert data["von"] == von.isoformat()
    assert data["bis"] == bis.isoformat()
    assert data["art"] == "Urlaub"
    absence_id = data["id"]

    # GET /api/absences
    response = client.get("/api/absences")
    assert response.status_code == 200
    absences = response.json()
    assert len(absences) >= 1
    assert any(a["id"] == absence_id for a in absences)


def test_absence_api_validation(client, setup_person_with_availability: Person):
    """Test: API validiert bis >= von."""
    person_id = setup_person_with_availability.id
    response = client.post(
        "/api/absences",
        json={
            "person_id": person_id,
            "von": date(2026, 7, 7).isoformat(),
            "bis": date(2026, 7, 1).isoformat(),  # bis < von
            "art": "Urlaub",
        },
    )
    assert response.status_code == 400
    assert "bis vor von" in response.text.lower()


def test_absence_api_filter_by_person(client, setup_person_with_availability: Person):
    """Test: GET /api/absences?person_id=X filtert."""
    person_id = setup_person_with_availability.id

    # Erstelle zwei Abwesenheiten
    for i, (von, bis) in enumerate([
        (date(2026, 7, 1), date(2026, 7, 7)),
        (date(2026, 8, 1), date(2026, 8, 7)),
    ]):
        response = client.post(
            "/api/absences",
            json={
                "person_id": person_id,
                "von": von.isoformat(),
                "bis": bis.isoformat(),
                "art": "Urlaub",
            },
        )
        assert response.status_code == 201

    # Filtere nach Person
    response = client.get(f"/api/absences?person_id={person_id}")
    assert response.status_code == 200
    absences = response.json()
    assert len(absences) >= 2
    assert all(a["person_id"] == person_id for a in absences)
