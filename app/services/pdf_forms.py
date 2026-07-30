"""PDF-Formulare zum handschriftlichen Ausfüllen (Verfügbarkeit / Abwesenheit)."""
from __future__ import annotations

import io
from dataclasses import dataclass

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.services.pdf_service import (
    ACCENT,
    BORDER,
    MUTED,
    PRIMARY,
    _register_font,
)

HOURS = [7, 16, 17, 18, 19]
DAYS = ["Mo", "Di", "Mi", "Do", "Fr"]
DAY_LABELS = {
    "Mo": "Montag",
    "Di": "Dienstag",
    "Mi": "Mittwoch",
    "Do": "Donnerstag",
    "Fr": "Freitag",
}
ABSENCE_ARTS = ["Urlaub", "Krankheit", "Dienstreise", "Entschuldigt", "Sonstiges"]
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
            fontSize=16,
            textColor=PRIMARY,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "sub": ParagraphStyle(
            "FormSub",
            parent=base["Normal"],
            fontName=font,
            fontSize=9,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceAfter=10,
        ),
        "body": ParagraphStyle(
            "FormBody",
            parent=base["Normal"],
            fontName=font,
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "hint": ParagraphStyle(
            "FormHint",
            parent=base["Normal"],
            fontName=font,
            fontSize=8,
            textColor=MUTED,
            leading=11,
            spaceBefore=8,
            spaceAfter=6,
        ),
        "cell": ParagraphStyle(
            "FormCell",
            parent=base["Normal"],
            fontName=font,
            fontSize=9,
            alignment=TA_CENTER,
            leading=12,
        ),
        "cell_left": ParagraphStyle(
            "FormCellL",
            parent=base["Normal"],
            fontName=font,
            fontSize=9,
            alignment=TA_LEFT,
            leading=12,
        ),
        "head": ParagraphStyle(
            "FormHead",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=9,
            textColor=colors.white,
            alignment=TA_CENTER,
            leading=12,
        ),
    }


def _field_line(label: str, value: str, styles: dict) -> Paragraph:
    fill = value if value else "________________________________"
    return Paragraph(f"<b>{label}:</b> {fill}", styles["body"])


def build_verfuegbarkeit_formular_pdf(
    personen: list[FormPerson] | None = None,
    *,
    periode_label: str = "",
) -> bytes:
    """Leeres Verfügbarkeits-Raster; optional eine Seite pro Person (Name vorausgefüllt)."""
    font = _register_font()
    font_bold = "AppSans-Bold" if font == "AppSans" else "Helvetica-Bold"
    styles = _styles(font, font_bold)

    pages = personen if personen else [FormPerson(name="", gremium="")]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Formular Verfügbarkeit",
    )

    story: list = []
    for idx, person in enumerate(pages):
        if idx:
            story.append(PageBreak())

        story.append(Paragraph("Verfügbarkeit – Sitzungsplanung", styles["title"]))
        story.append(
            Paragraph(
                "Bitte ankreuzen, zu welchen Stunden Sie grundsätzlich verfügbar sind. "
                "Das Formular wird vom Amt in den AusschussPlaner übernommen.",
                styles["sub"],
            )
        )
        story.append(_field_line("Name", person.name, styles))
        story.append(_field_line("Gremium", person.gremium, styles))
        story.append(_field_line("Periode / Gültig ab", periode_label, styles))
        story.append(Spacer(1, 4 * mm))

        header = [Paragraph("", styles["head"])] + [
            Paragraph(f"{h:02d}:00", styles["head"]) for h in HOURS
        ]
        data = [header]
        for day in DAYS:
            row = [Paragraph(DAY_LABELS[day], styles["cell_left"])]
            for _ in HOURS:
                row.append(Paragraph(CHECK, styles["cell"]))
            data.append(row)

        col0 = 32 * mm
        rest = (A4[0] - 28 * mm - col0) / len(HOURS)
        table = Table(data, colWidths=[col0] + [rest] * len(HOURS), rowHeights=[10 * mm] + [12 * mm] * 5)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                    ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f3f4f6")),
                    ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
                    ("BOX", (0, 0), (-1, -1), 1.0, PRIMARY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(table)
        story.append(
            Paragraph(
                "Hinweis: Es zählen volle Stunden (07, 16, 17, 18, 19 Uhr). "
                "Ein 90‑Minuten-Termin (z. B. 17:00–18:30) erfordert Verfügbarkeit in beiden Stunden.",
                styles["hint"],
            )
        )
        story.append(Spacer(1, 8 * mm))
        story.append(
            Paragraph(
                "<b>Datum:</b> _______________ &nbsp;&nbsp;&nbsp; "
                "<b>Unterschrift:</b> ________________________________",
                styles["body"],
            )
        )

    doc.build(story)
    return buf.getvalue()


def build_abwesenheit_formular_pdf(
    personen: list[FormPerson] | None = None,
    *,
    rows: int = 8,
) -> bytes:
    """Leeres Abwesenheits-Formular; optional eine Seite pro Person."""
    font = _register_font()
    font_bold = "AppSans-Bold" if font == "AppSans" else "Helvetica-Bold"
    styles = _styles(font, font_bold)

    pages = personen if personen else [FormPerson(name="", gremium="")]
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title="Formular Abwesenheiten",
    )

    story: list = []
    for idx, person in enumerate(pages):
        if idx:
            story.append(PageBreak())

        block: list = []
        block.append(Paragraph("Abwesenheiten – Sitzungsplanung", styles["title"]))
        block.append(
            Paragraph(
                "Bitte geplante Abwesenheiten eintragen. Das Formular wird vom Amt "
                "in den AusschussPlaner übernommen.",
                styles["sub"],
            )
        )
        block.append(_field_line("Name", person.name, styles))
        block.append(_field_line("Gremium", person.gremium, styles))
        block.append(Spacer(1, 3 * mm))
        block.append(
            Paragraph(
                f"<b>Art</b> (eine wählen): {' / '.join(ABSENCE_ARTS)}",
                styles["hint"],
            )
        )

        header = [
            Paragraph("Von<br/>(TT.MM.JJJJ)", styles["head"]),
            Paragraph("Bis<br/>(TT.MM.JJJJ)", styles["head"]),
            Paragraph("Art", styles["head"]),
            Paragraph("Bemerkung", styles["head"]),
        ]
        data = [header]
        for _ in range(rows):
            data.append(
                [
                    Paragraph("", styles["cell"]),
                    Paragraph("", styles["cell"]),
                    Paragraph("", styles["cell"]),
                    Paragraph("", styles["cell"]),
                ]
            )

        usable = A4[0] - 28 * mm
        widths = [usable * 0.2, usable * 0.2, usable * 0.22, usable * 0.38]
        table = Table(data, colWidths=widths, rowHeights=[12 * mm] + [11 * mm] * rows)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                    ("GRID", (0, 0), (-1, -1), 0.6, BORDER),
                    ("BOX", (0, 0), (-1, -1), 1.0, PRIMARY),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
                ]
            )
        )
        block.append(table)
        block.append(
            Paragraph(
                "Falls Sie keine Abwesenheiten haben: Feld leer lassen bzw. "
                "„keine“ vermerken und unterschreiben.",
                styles["hint"],
            )
        )
        block.append(Spacer(1, 8 * mm))
        block.append(
            Paragraph(
                "<b>Datum:</b> _______________ &nbsp;&nbsp;&nbsp; "
                "<b>Unterschrift:</b> ________________________________",
                styles["body"],
            )
        )
        story.append(KeepTogether(block))

    doc.build(story)
    return buf.getvalue()
