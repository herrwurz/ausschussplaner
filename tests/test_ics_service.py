"""Tests für ICS-Export."""
from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.models.enums import Wochentag
from app.services.ics_service import build_sitzungen_ics


def test_build_sitzungen_ics_contains_event():
    v = SimpleNamespace(
        id=42,
        ausschuss_id=1,
        woche=1,
        wochentag=Wochentag.MO,
        start_minute=16 * 60,
        end_minute=17 * 60 + 30,
        quote=100,
        planungs_start_datum=date(2026, 3, 2),
    )
    ics = build_sitzungen_ics([v], ausschuss_namen={1: "Sport"})
    assert "BEGIN:VCALENDAR" in ics
    assert "BEGIN:VEVENT" in ics
    assert "SUMMARY:Sport" in ics
    assert "DTSTART:20260302T160000" in ics
    assert "DTEND:20260302T173000" in ics
