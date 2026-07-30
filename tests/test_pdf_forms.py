"""Tests für getrennte PDF-Formulare."""
from __future__ import annotations

from app.services.pdf_forms import (
    FormPerson,
    build_abwesenheit_formular_pdf,
    build_verfuegbarkeit_formular_pdf,
)


def test_verfuegbarkeit_formular():
    pdf = build_verfuegbarkeit_formular_pdf(
        [FormPerson("Andreas Hofreither", "Stadtrat")],
        periode_label="P1",
    )
    assert pdf.startswith(b"%PDF")


def test_abwesenheit_formular():
    pdf = build_abwesenheit_formular_pdf(
        [FormPerson("Andreas Hofreither", "Stadtrat"), FormPerson("Max Mustermann", "")],
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 500
