"""PDF-Export für Sitzungs-Wochenpläne."""
from __future__ import annotations

import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app.models.enums import Wochentag
from app.models.models import Ausschuss, Sitzungsvorschlag

PRIMARY = colors.HexColor("#1e3a8a")
ACCENT = colors.HexColor("#fbbf24")
LIGHT_BG = colors.HexColor("#f0f4ff")
BORDER = colors.HexColor("#d1d5db")
MUTED = colors.HexColor("#6b7280")

DAY_ORDER = [Wochentag.MO, Wochentag.DI, Wochentag.MI, Wochentag.DO, Wochentag.FR]
DAY_OFFSET = {
    Wochentag.MO: 0,
    Wochentag.DI: 1,
    Wochentag.MI: 2,
    Wochentag.DO: 3,
    Wochentag.FR: 4,
}
DAY_ALIASES = {
    "MO": Wochentag.MO,
    "DI": Wochentag.DI,
    "MI": Wochentag.MI,
    "DO": Wochentag.DO,
    "FR": Wochentag.FR,
    "MONTAG": Wochentag.MO,
    "DIENSTAG": Wochentag.DI,
    "MITTWOCH": Wochentag.MI,
    "DONNERSTAG": Wochentag.DO,
    "FREITAG": Wochentag.FR,
}

_FONT_REGISTERED = False
_FONT_NAME = "Helvetica"


@dataclass(frozen=True)
class PlanTermin:
    """Ein Eintrag im PDF-Wochenraster (unabhängig von der DB)."""

    ausschuss_id: int
    ausschuss_name: str
    woche: int
    wochentag: Wochentag
    start_minute: int
    end_minute: int
    quote: int | None = None


def _register_font() -> str:
    """Registriert eine Unicode-fähige Systemschrift (Umlaute)."""
    global _FONT_REGISTERED, _FONT_NAME
    if _FONT_REGISTERED:
        return _FONT_NAME

    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for path in candidates:
        if path.exists():
            try:
                pdfmetrics.registerFont(TTFont("AppSans", str(path)))
                bold_candidates = [
                    path.with_name("arialbd.ttf"),
                    path.with_name("calibrib.ttf"),
                    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
                    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                ]
                for b in bold_candidates:
                    if b.exists():
                        pdfmetrics.registerFont(TTFont("AppSans-Bold", str(b)))
                        break
                else:
                    pdfmetrics.registerFont(TTFont("AppSans-Bold", str(path)))
                _FONT_NAME = "AppSans"
                _FONT_REGISTERED = True
                return _FONT_NAME
            except Exception:
                continue

    _FONT_REGISTERED = True
    return _FONT_NAME


def _minutes_to_time(minutes: int) -> str:
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def parse_time_to_minutes(value: str) -> int:
    """'16:00' oder '16.00' → Minuten seit Mitternacht."""
    cleaned = value.strip().replace(".", ":")
    parts = cleaned.split(":")
    return int(parts[0]) * 60 + int(parts[1] if len(parts) > 1 else 0)


def parse_wochentag(value: str | Wochentag) -> Wochentag:
    if isinstance(value, Wochentag):
        return value
    key = value.strip().upper()
    if key in DAY_ALIASES:
        return DAY_ALIASES[key]
    if "." in key:
        key = key.split(".")[-1]
    if key in DAY_ALIASES:
        return DAY_ALIASES[key]
    return Wochentag[key]


def _day_label(weekday: Wochentag, week: int, anchor: date | None) -> str:
    if anchor is None:
        return weekday.value
    d = anchor + timedelta(days=(week - 1) * 7 + DAY_OFFSET[weekday])
    return f"{weekday.value}<br/>{d.strftime('%d.%m.%Y')}"


def vorschlaege_to_plan(
    vorschlaege: list[Sitzungsvorschlag],
    ausschuss_namen: dict[int, str],
) -> list[PlanTermin]:
    return [
        PlanTermin(
            ausschuss_id=v.ausschuss_id,
            ausschuss_name=ausschuss_namen.get(v.ausschuss_id, f"Ausschuss #{v.ausschuss_id}"),
            woche=v.woche,
            wochentag=v.wochentag,
            start_minute=v.start_minute,
            end_minute=v.end_minute,
            quote=v.quote or None,
        )
        for v in vorschlaege
    ]


def build_wochenplan_pdf(
    termine: list[PlanTermin],
    *,
    titel: str = "Sitzungsplan Ausschüsse",
    untertitel: str | None = None,
    start_datum: date | None = None,
) -> bytes:
    """Erzeugt ein landscape-A4-PDF mit Wochenraster (Mo–Fr)."""
    font = _register_font()
    font_bold = "AppSans-Bold" if font == "AppSans" else "Helvetica-Bold"

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=12 * mm,
        bottomMargin=12 * mm,
        title=titel,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleDE",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=18,
        textColor=PRIMARY,
        alignment=TA_CENTER,
        spaceAfter=4,
    )
    sub_style = ParagraphStyle(
        "SubDE",
        parent=styles["Normal"],
        fontName=font,
        fontSize=10,
        textColor=MUTED,
        alignment=TA_CENTER,
        spaceAfter=12,
    )
    cell_style = ParagraphStyle(
        "CellDE",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        leading=11,
        alignment=TA_LEFT,
    )
    header_style = ParagraphStyle(
        "HeadDE",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=9,
        textColor=colors.white,
        alignment=TA_CENTER,
        leading=12,
    )
    week_style = ParagraphStyle(
        "WeekDE",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=12,
        textColor=PRIMARY,
        spaceBefore=8,
        spaceAfter=6,
    )
    empty_style = ParagraphStyle(
        "EmptyDE",
        parent=styles["Normal"],
        fontName=font,
        fontSize=8,
        textColor=MUTED,
        alignment=TA_CENTER,
    )

    story: list = []
    story.append(Paragraph(titel, title_style))
    if untertitel:
        story.append(Paragraph(untertitel, sub_style))
    else:
        story.append(Spacer(1, 6))

    if not termine:
        story.append(Paragraph("Keine Termine vorhanden.", cell_style))
        doc.build(story)
        return buf.getvalue()

    anchor = start_datum
    by_week: dict[int, dict[Wochentag, list[PlanTermin]]] = defaultdict(lambda: defaultdict(list))
    for t in termine:
        by_week[t.woche][t.wochentag].append(t)

    for week in sorted(by_week):
        if anchor is not None:
            week_start = anchor + timedelta(days=(week - 1) * 7)
            week_end = week_start + timedelta(days=4)
            week_title = (
                f"Woche {week} "
                f"({week_start.strftime('%d.%m.')} – {week_end.strftime('%d.%m.%Y')})"
            )
        else:
            week_title = f"Woche {week}"
        story.append(Paragraph(week_title, week_style))

        header = [Paragraph(_day_label(d, week, anchor), header_style) for d in DAY_ORDER]
        row: list = []
        for day in DAY_ORDER:
            entries = sorted(by_week[week].get(day, []), key=lambda x: x.start_minute)
            if not entries:
                row.append(Paragraph("—", empty_style))
                continue
            parts = []
            for e in entries:
                zeit = f"{_minutes_to_time(e.start_minute)}–{_minutes_to_time(e.end_minute)}"
                quote = f" · {e.quote}%" if e.quote else ""
                parts.append(f"<b>{e.ausschuss_name}</b><br/>{zeit}{quote}")
            row.append(Paragraph("<br/><br/>".join(parts), cell_style))

        col_w = (landscape(A4)[0] - 24 * mm) / 5
        table = Table([header, row], colWidths=[col_w] * 5, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), PRIMARY),
                    ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BG),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, -1), font),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("ALIGN", (0, 0), (-1, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("BOX", (0, 0), (-1, -1), 0.8, PRIMARY),
                    ("INNERGRID", (0, 0), (-1, -1), 0.4, BORDER),
                    ("LINEBELOW", (0, 0), (-1, 0), 1.5, ACCENT),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [LIGHT_BG, colors.white]),
                    ("MINROWHEIGHT", (0, 1), (-1, 1), 45 * mm),
                ]
            )
        )
        story.append(table)

    footer = Paragraph(
        f"Erstellt am {date.today().strftime('%d.%m.%Y')} · AusschussPlaner",
        ParagraphStyle(
            "FootDE",
            parent=styles["Normal"],
            fontName=font,
            fontSize=8,
            textColor=MUTED,
            alignment=TA_CENTER,
            spaceBefore=16,
        ),
    )
    story.append(footer)
    doc.build(story)
    return buf.getvalue()


def load_ausschuss_namen(db, ausschuss_ids: set[int]) -> dict[int, str]:
    if not ausschuss_ids:
        return {}
    rows = db.query(Ausschuss).filter(Ausschuss.id.in_(ausschuss_ids)).all()
    return {a.id: a.name for a in rows}
