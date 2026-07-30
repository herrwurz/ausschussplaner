"""Tests für den GR-Erhebungsbogen."""
from __future__ import annotations

from app.services.pdf_forms import FormPerson, build_gr_erhebungsbogen_pdf


def test_erhebungsbogen_empty_persons():
    pdf = build_gr_erhebungsbogen_pdf([])
    assert pdf.startswith(b"%PDF")


def test_erhebungsbogen_with_persons():
    pdf = build_gr_erhebungsbogen_pdf(
        [
            FormPerson("Andreas Hofreither", "Stadtrat"),
            FormPerson("Kerstin Suchan-Mayr", "Bürgermeisterin"),
        ],
        periode_label="P1 2025–2029",
    )
    assert pdf.startswith(b"%PDF")
    assert len(pdf) > 800
