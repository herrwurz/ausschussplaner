"""Ein PDF-Formular für die GR: alle Personen, Abwesenheit + Verfügbarkeits-Uhrzeiten."""
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


def build_gr_erhebungsbogen_pdf(
    personen: list[FormPerson],
    *,
    periode_label: str = "",
) -> bytes:
    """Ein Blatt: Name | Abwesenheit (leer) | 07:00 … 19:00 (Ankreuzen)."""
    font = _register_font()
    font_bold = "AppSans-Bold" if font == "AppSans" else "Helvetica-Bold"
    styles = _styles(font, font_bold)

    buf = io.BytesIO()
    page = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page,
        leftMargin=10 * mm,
        rightMargin=10 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
        title="Erhebungsbogen Verfügbarkeit und Abwesenheit",
    )

    story: list = []
    titel = "Erhebungsbogen – Verfügbarkeit & Abwesenheit"
    if periode_label:
        titel += f" ({periode_label})"
    story.append(Paragraph(titel, styles["title"]))
    story.append(
        Paragraph(
            "Bitte ausfüllen und zurückgeben. Einträge werden vom Amt in den AusschussPlaner übernommen. "
            "Verfügbarkeit: typische Woche Mo–Fr anklicken. Abwesenheit: z. B. Urlaub 01.08.–15.08.",
            styles["sub"],
        )
    )

    header = [
        Paragraph("Name", styles["head"]),
        Paragraph("Abwesenheit<br/>(von–bis / Art)", styles["head"]),
    ] + [Paragraph(f"{h:02d}:00", styles["head"]) for h in HOURS]

    data = [header]
    for person in personen:
        label = person.name
        if person.gremium:
            label = f"{person.name}<br/><font size='7' color='#6b7280'>{person.gremium}</font>"
        row = [
            Paragraph(label, styles["cell_left"]),
            Paragraph("", styles["cell"]),  # leere Zeile zum Eintragen
        ] + [Paragraph(CHECK, styles["cell"]) for _ in HOURS]
        data.append(row)

    if len(data) == 1:
        data.append(
            [
                Paragraph("— keine aktiven Personen —", styles["cell_left"]),
                Paragraph("", styles["cell"]),
            ]
            + [Paragraph(CHECK, styles["cell"]) for _ in HOURS]
        )

    usable = page[0] - 20 * mm
    name_w = usable * 0.22
    abs_w = usable * 0.28
    hour_w = (usable - name_w - abs_w) / len(HOURS)
    col_widths = [name_w, abs_w] + [hour_w] * len(HOURS)
    row_h = 9 * mm
    table = Table(data, colWidths=col_widths, rowHeights=[11 * mm] + [row_h] * (len(data) - 1), repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                ("BACKGROUND", (0, 1), (0, -1), colors.HexColor("#f3f4f6")),
                ("BACKGROUND", (1, 1), (1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BOX", (0, 0), (-1, -1), 1.0, PRIMARY),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (2, 1), (-1, -1), "CENTER"),
                ("LINEBELOW", (0, 0), (-1, 0), 1.2, ACCENT),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 4 * mm))
    story.append(
        Paragraph(
            "Uhrzeiten = grundsätzlich verfügbar (Mo–Fr). Ausnahmen und Urlaub/Krankheit bitte in der Spalte "
            "„Abwesenheit“ eintragen. &nbsp;&nbsp; Datum: _____________ &nbsp;&nbsp; "
            "Bearbeiter/Amt: _____________________",
            styles["hint"],
        )
    )

    doc.build(story)
    return buf.getvalue()


# Rückwärtskompatible Aliase (Tests/alte Aufrufe)
def build_verfuegbarkeit_formular_pdf(personen=None, *, periode_label: str = "") -> bytes:
    return build_gr_erhebungsbogen_pdf(personen or [], periode_label=periode_label)


def build_abwesenheit_formular_pdf(personen=None, *, rows: int = 8) -> bytes:
    return build_gr_erhebungsbogen_pdf(personen or [])
