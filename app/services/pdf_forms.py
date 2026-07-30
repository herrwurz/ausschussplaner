"""Zwei getrennte PDF-Formulare für die GR (jeweils alle Personen in einer Tabelle)."""
from __future__ import annotations

import io
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.services.pdf_service import ACCENT, BORDER, MUTED, PRIMARY, _register_font

HOURS = [7, 16, 17, 18, 19]
CHECK = "☐"


@dataclass(frozen=True)
class FormPerson:
    name: str
    gremium: str = ""


def _styles(font: str, font_bold: str) -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "FormTitle",
            parent=base["Heading1"],
            fontName=font_bold,
            fontSize=14,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=2,
        ),
        "sub": ParagraphStyle(
            "FormSub",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "hint": ParagraphStyle(
            "FormHint",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            textColor=MUTED,
            leading=11,
            spaceBefore=6,
        ),
        "cell": ParagraphStyle(
            "FormCell",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            alignment=TA_CENTER,
            leading=10,
        ),
        "cell_left": ParagraphStyle(
            "FormCellL",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            alignment=TA_LEFT,
            leading=10,
        ),
        "head": ParagraphStyle(
            "FormHead",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=8,
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=10,
        ),
    }


def _name_cell(person: FormPerson, styles: dict) -> Paragraph:
    label = person.name
    if person.gremium:
        label = f"{person.name}<br/><font size='7' color='#6b7280'>{person.gremium}</font>"
    return Paragraph(label, styles["cell_left"])


def _table_style() -> TableStyle:
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
            ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f3f4f6")),
            ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
            ("BOX", (0, 0), (-1, -1), 1.0, PRIMARY),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("LINEBELOW", (0, 0), (-1, 0), 1.2, ACCENT),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 2),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
        ]
    )


def build_verfuegbarkeit_formular_pdf(
    personen: list[FormPerson] | None = None,
    *,
    periode_label: str = "",
) -> bytes:
    """Verfügbarkeit: Name | 07:00 | 16:00 | 17:00 | 18:00 | 19:00."""
    font = _register_font()
    font_bold = "AppSans-Bold" if font == "AppSans" else "Helvetica-Bold"
    styles = _styles(font, font_bold)
    personen = personen or []

    buf = io.BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Formular Verfügbarkeit",
    )

    story: list = []
    titel = "Verfügbarkeit – Sitzungsplanung"
    if periode_label:
        titel += f" ({periode_label})"
    story.append(Paragraph(titel, styles["title"]))
    story.append(
        Paragraph(
            "Bitte ankreuzen, zu welchen Stunden Sie typischerweise Mo–Fr verfügbar sind. "
            "Das Formular wird vom Amt in den AusschussPlaner übernommen.",
            styles["sub"],
        )
    )

    header = [Paragraph("Name", styles["head"])] + [
        Paragraph(f"{h:02d}:00", styles["head"]) for h in HOURS
    ]
    data = [header]
    for person in personen:
        data.append(
            [_name_cell(person, styles)] + [Paragraph(CHECK, styles["cell"]) for _ in HOURS]
        )
    if len(data) == 1:
        data.append(
            [Paragraph("— keine aktiven Personen —", styles["cell_left"])]
            + [Paragraph(CHECK, styles["cell"]) for _ in HOURS]
        )

    usable = page[0] - 20 * mm
    name_w = usable * 0.28
    hour_w = (usable - name_w) / len(HOURS)
    table = Table(
        data,
        colWidths=[name_w] + [hour_w] * len(HOURS),
        rowHeights=[11 * mm] + [9 * mm] * (len(data) - 1),
        repeatRows=1,
    )
    style = _table_style()
    style.add("ALIGN", (1, 1), (-1, -1), "CENTER")
    table.setStyle(style)
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Datum: _____________ &nbsp;&nbsp; Zurück an: _____________________",
            styles["hint"],
        )
    )
    doc.build(story)
    return buf.getvalue()


def build_abwesenheit_formular_pdf(
    personen: list[FormPerson] | None = None,
    *,
    rows: int = 8,  # ungenutzt — eine Zeile je Person
) -> bytes:
    """Abwesenheit: Name | leere Spalte zum Eintragen."""
    font = _register_font()
    font_bold = "AppSans-Bold" if font == "AppSans" else "Helvetica-Bold"
    styles = _styles(font, font_bold)
    personen = personen or []

    buf = io.BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Formular Abwesenheiten",
    )

    story: list = []
    story.append(Paragraph("Abwesenheiten – Sitzungsplanung", styles["title"]))
    story.append(
        Paragraph(
            "Bitte geplante Abwesenheiten eintragen (z. B. Urlaub 01.08.–15.08. oder Krankheit). "
            "Keine Abwesenheit: Zeile leer lassen. Das Formular wird vom Amt übernommen.",
            styles["sub"],
        )
    )

    header = [
        Paragraph("Name", styles["head"]),
        Paragraph("Abwesenheit (von–bis / Art / Bemerkung)", styles["head"]),
    ]
    data = [header]
    for person in personen:
        data.append([_name_cell(person, styles), Paragraph("", styles["cell"])])
    if len(data) == 1:
        data.append(
            [Paragraph("— keine aktiven Personen —", styles["cell_left"]), Paragraph("", styles["cell"])]
        )

    usable = page[0] - 20 * mm
    name_w = usable * 0.28
    abs_w = usable - name_w
    table = Table(
        data,
        colWidths=[name_w, abs_w],
        rowHeights=[11 * mm] + [11 * mm] * (len(data) - 1),
        repeatRows=1,
    )
    table.setStyle(_table_style())
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Arten z. B.: Urlaub / Krankheit / Dienstreise / Entschuldigt / Sonstiges. "
            "&nbsp;&nbsp; Datum: _____________ &nbsp;&nbsp; Zurück an: _____________________",
            styles["hint"],
        )
    )
    doc.build(story)
    return buf.getvalue()
