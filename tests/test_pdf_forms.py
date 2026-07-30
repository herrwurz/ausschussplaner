"""Tests für PDF-Ausfüllformulare."""
from __future__ import annotations

from app.services.pdf_forms import (
    FormPerson,
    build_abwesenheit_formular_pdf,
    build_verfuegbarkeit_formular_pdf,
)


def test_verfuegbarkeit_formular_blank():
    pdf = build_verfuegbarkeit_formular_pdf(None)
    assert pdf.startswith(b"%PDF")


def test_verfuegbarkeit_formular_with_persons():
    pdf = build_verfuegbarkeit_formular_pdf(
        [FormPerson("Andreas Hofreither", "Stadtrat"), FormPerson("Test Person", "Gemeinderat")],
        periode_label="P1 2025–2029",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 1000


def test_abwesenheit_formular_blank_and_named():
    blank = build_abwesenheit_formular_pdf(None)
    named = build_abwesenheit_formular_pdf([FormPerson("Max Mustermann", "Gemeinderat")])
    assert blank.startswith(b"%PDF")
    assert named.startswith(b"%PDF")
