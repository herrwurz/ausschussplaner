"""Tests für PDF-Wochenplan-Export."""
from __future__ import annotations

from datetime import date

from app.models.enums import Wochentag
from app.services.pdf_service import PlanTermin, build_wochenplan_pdf, parse_wochentag


def test_build_wochenplan_pdf_empty():
    pdf = build_wochenplan_pdf([])
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 100


def test_build_wochenplan_pdf_with_slots():
    rows = [
        PlanTermin(1, "Sport", 1, Wochentag.MO, 16 * 60, 17 * 60 + 30, 100),
        PlanTermin(2, "Bildung", 1, Wochentag.DI, 17 * 60, 18 * 60 + 30, 80),
        PlanTermin(3, "Kontrolle", 2, Wochentag.FR, 7 * 60, 8 * 60 + 30, None),
    ]
    pdf = build_wochenplan_pdf(
        rows,
        titel="Sitzungsplan Ausschüsse",
        untertitel="Planungsstart: 02.03.2026",
        start_datum=date(2026, 3, 2),
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500


def test_parse_wochentag_aliases():
    assert parse_wochentag("Mo") is Wochentag.MO
    assert parse_wochentag("DI") is Wochentag.DI
    assert parse_wochentag("Mittwoch") is Wochentag.MI
